"""管理员控制器"""
from flask import Blueprint, request, jsonify, current_app
from app.models.db_users import User
from app.extensions import db
from app.controllers.auth_controller import token_required

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    """管理员权限验证装饰器"""
    @token_required
    def decorated(current_user, *args, **kwargs):
        if not current_user.is_admin():
            return jsonify({'message': '需要管理员权限'}), 403
        return f(current_user, *args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated


def resource_owner_or_admin(resource_user_id):
    """检查当前用户是否是资源所有者或管理员"""
    def decorator(f):
        @token_required
        def decorated(current_user, *args, **kwargs):
            # 管理员可以访问所有资源
            if current_user.is_admin():
                return f(current_user, *args, **kwargs)

            # 检查资源所有者
            if resource_user_id is not None and resource_user_id != current_user.id:
                return jsonify({'message': '无权访问此资源'}), 403

            return f(current_user, *args, **kwargs)
        decorated.__name__ = f.__name__
        return decorated
    return decorator

@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_all_users(current_user):
    """获取所有用户列表（管理员功能）"""
    try:
        users = User.query.all()
        users_data = [user.to_safe_dict() for user in users]

        return jsonify({
            'users': users_data,
            'total': len(users_data)
        }), 200

    except Exception as e:
        current_app.logger.error(f'获取用户列表错误: {str(e)}')
        return jsonify({'message': '获取用户列表失败'}), 500

@admin_bp.route('/users', methods=['POST'])
@admin_required
def create_user(current_user):
    """创建新用户（管理员功能）"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'message': '请求数据不能为空'}), 400

        required_fields = ['username', 'email']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'message': f'{field}不能为空'}), 400

        username = data['username']
        email = data['email']

        # 验证用户名长度
        if len(username) < 3 or len(username) > 20:
            return jsonify({'message': '用户名长度必须在3-20个字符之间'}), 400

        # 检查用户名是否已存在
        if User.query.filter_by(username=username).first():
            return jsonify({'message': '用户名已存在'}), 409

        # 检查邮箱是否已存在
        if User.query.filter_by(email=email).first():
            return jsonify({'message': '邮箱已被注册'}), 409

        # 创建新用户
        new_user = User(
            username=username,
            email=email,
            full_name=data.get('full_name', ''),
            department=data.get('department', ''),
            position=data.get('position', ''),
            role=data.get('role', 'user'),
            status=data.get('status', 'active')
        )

        # 如果提供了密码，则设置密码；否则生成默认密码
        if data.get('password'):
            new_user.set_password(data['password'])
        else:
            # 生成默认密码（用户名+123）
            default_password = f"{username}123"
            new_user.set_password(default_password)

        db.session.add(new_user)
        db.session.commit()

        user_data = new_user.to_safe_dict()
        # 如果是生成的默认密码，在响应中提示
        if not data.get('password'):
            user_data['default_password'] = default_password

        return jsonify({
            'message': '用户创建成功',
            'user': user_data
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'创建用户错误: {str(e)}')
        return jsonify({'message': '创建用户失败，请稍后重试'}), 500

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(current_user, user_id):
    """更新用户信息（管理员功能）"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'message': '用户不存在'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'message': '请求数据不能为空'}), 400

        # 更新允许的字段
        allowed_fields = ['full_name', 'email', 'department', 'position', 'role', 'status']
        for field in allowed_fields:
            if field in data:
                # 特殊处理邮箱冲突检查
                if field == 'email' and data[field] != user.email:
                    if User.query.filter_by(email=data[field]).first():
                        return jsonify({'message': '邮箱已被其他用户使用'}), 409
                setattr(user, field, data[field])

        # 如果提供了新密码，则更新密码
        if data.get('password'):
            if len(data['password']) < 6:
                return jsonify({'message': '密码长度至少6位'}), 400
            user.set_password(data['password'])

        db.session.commit()

        return jsonify({
            'message': '用户信息更新成功',
            'user': user.to_safe_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'更新用户错误: {str(e)}')
        return jsonify({'message': '更新用户失败，请稍后重试'}), 500

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(current_user, user_id):
    """删除用户（管理员功能）"""
    try:
        # 不允许删除超级管理员账户
        if user_id == 1:  # 假设ID为1的是超级管理员
            return jsonify({'message': '不能删除超级管理员账户'}), 403

        user = User.query.get(user_id)
        if not user:
            return jsonify({'message': '用户不存在'}), 404

        # 不允许删除当前登录的管理员自己
        if user.id == current_user.id:
            return jsonify({'message': '不能删除当前登录账户'}), 403

        db.session.delete(user)
        db.session.commit()

        return jsonify({'message': '用户删除成功'}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'删除用户错误: {str(e)}')
        return jsonify({'message': '删除用户失败，请稍后重试'}), 500

@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def reset_user_password(current_user, user_id):
    """重置用户密码（管理员功能）"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'message': '用户不存在'}), 404

        # 生成新密码（用户名+123）
        new_password = f"{user.username}123"
        user.set_password(new_password)

        # 重置登录失败次数和锁定状态
        user.reset_login_attempts()

        db.session.commit()

        return jsonify({
            'message': '密码重置成功',
            'new_password': new_password
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'重置密码错误: {str(e)}')
        return jsonify({'message': '密码重置失败，请稍后重试'}), 500

@admin_bp.route('/stats', methods=['GET'])
@admin_required
def get_system_stats(current_user):
    """获取系统统计信息（管理员功能）"""
    try:
        from app.models.db_models import Model
        from app.models.db_tasks import Task
        from app.models.db_datasets import Dataset

        # 用户统计
        total_users = User.query.count()
        active_users = User.query.filter_by(status='active').count()
        admin_users = User.query.filter_by(role='admin').count()

        # 模型统计
        total_models = Model.query.count()
        available_models = Model.query.filter_by(status='available').count()

        # 任务统计
        total_tasks = Task.query.count()
        running_tasks = Task.query.filter_by(status='running').count()
        completed_tasks = Task.query.filter_by(status='completed').count()

        # 数据集统计
        total_datasets = Dataset.query.count()

        return jsonify({
            'stats': {
                'users': {
                    'total': total_users,
                    'active': active_users,
                    'admin': admin_users
                },
                'models': {
                    'total': total_models,
                    'available': available_models
                },
                'tasks': {
                    'total': total_tasks,
                    'running': running_tasks,
                    'completed': completed_tasks
                },
                'datasets': {
                    'total': total_datasets
                }
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f'获取统计信息错误: {str(e)}')
        return jsonify({'message': '获取统计信息失败'}), 500


# ===== 模型管理功能 =====

@admin_bp.route('/models', methods=['GET'])
@token_required
def get_all_models(current_user):
    """获取模型列表（用户只能看到自己的，管理员可以看到所有）"""
    try:
        from app.models.db_models import Model

        # 解析查询参数
        model_type = request.args.get('model_type')
        status = request.args.get('status')
        source = request.args.get('source')

        query = Model.query

        # 权限检查：普通用户只能看到自己的模型和官方模型
        if not current_user.is_admin():
            query = query.filter(
                (Model.user_id == current_user.id) |
                (Model.model_source == 'official') |
                (Model.is_predefined == True)
            )

        # 应用筛选条件
        if model_type:
            query = query.filter_by(model_type=model_type)
        if status:
            query = query.filter_by(status=status)
        if source:
            query = query.filter_by(model_source=source)

        models = query.order_by(Model.created_at.desc()).all()
        models_data = [model.to_dict() for model in models]

        return jsonify({
            'models': models_data,
            'total': len(models_data)
        }), 200

    except Exception as e:
        current_app.logger.error(f'获取模型列表错误: {str(e)}')
        return jsonify({'message': '获取模型列表失败'}), 500


@admin_bp.route('/models', methods=['POST'])
@token_required
def create_model(current_user):
    """创建新模型（用户创建自己的模型）"""
    try:
        from app.models.db_models import Model

        data = request.get_json()

        if not data:
            return jsonify({'message': '请求数据不能为空'}), 400

        required_fields = ['model_name', 'model_type', 'model_path', 'tokenizer_path']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'message': f'{field}不能为空'}), 400

        # 检查模型名称是否已存在（全局唯一）
        if Model.query.filter_by(model_name=data['model_name']).first():
            return jsonify({'message': '模型名称已存在'}), 409

        # 创建新模型，设置用户ID
        new_model = Model(
            model_name=data['model_name'],
            model_type=data['model_type'],
            description=data.get('description', ''),
            model_path=data['model_path'],
            tokenizer_path=data['tokenizer_path'],
            mlm_model_path=data.get('mlm_model_path'),
            checkpoint_path=data.get('checkpoint_path'),
            model_source='user',  # 用户上传的模型
            max_length=data.get('max_length', 512),
            status=data.get('status', 'available'),
            supported_tasks=data.get('supported_tasks', []),
            is_predefined=False,  # 用户上传的模型不是预定义的
            user_id=current_user.id  # 设置创建者
        )

        db.session.add(new_model)
        db.session.commit()

        return jsonify({
            'message': '模型创建成功',
            'model': new_model.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'创建模型错误: {str(e)}')
        return jsonify({'message': '创建模型失败，请稍后重试'}), 500


@admin_bp.route('/models/<int:model_id>', methods=['PUT'])
@token_required
def update_model(current_user, model_id):
    """更新模型信息（用户只能更新自己的模型，管理员可以更新所有）"""
    try:
        from app.models.db_models import Model

        model = Model.query.get(model_id)
        if not model:
            return jsonify({'message': '模型不存在'}), 404

        # 权限检查：用户只能更新自己的模型或预定义模型（但不能修改预定义模型的核心属性）
        if not current_user.is_admin():
            if model.user_id != current_user.id:
                return jsonify({'message': '无权修改此模型'}), 403
            if model.is_predefined:
                return jsonify({'message': '不能修改预定义模型'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'message': '请求数据不能为空'}), 400

        # 更新允许的字段
        allowed_fields = [
            'model_name', 'model_type', 'description', 'model_path', 'tokenizer_path',
            'mlm_model_path', 'checkpoint_path', 'model_source', 'max_length',
            'status', 'supported_tasks'
        ]

        # 管理员可以修改所有字段，普通用户不能修改is_predefined
        if current_user.is_admin():
            allowed_fields.append('is_predefined')

        for field in allowed_fields:
            if field in data:
                # 特殊处理模型名称冲突检查
                if field == 'model_name' and data[field] != model.model_name:
                    if Model.query.filter_by(model_name=data[field]).first():
                        return jsonify({'message': '模型名称已被其他模型使用'}), 409
                setattr(model, field, data[field])

        db.session.commit()

        return jsonify({
            'message': '模型信息更新成功',
            'model': model.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'更新模型错误: {str(e)}')
        return jsonify({'message': '更新模型失败，请稍后重试'}), 500


@admin_bp.route('/models/<int:model_id>', methods=['DELETE'])
@token_required
def delete_model(current_user, model_id):
    """删除模型（用户只能删除自己的模型，管理员可以删除所有）"""
    try:
        from app.models.db_models import Model
        from app.models.db_tasks import Task

        model = Model.query.get(model_id)
        if not model:
            return jsonify({'message': '模型不存在'}), 404

        # 权限检查
        if not current_user.is_admin():
            if model.user_id != current_user.id:
                return jsonify({'message': '无权删除此模型'}), 403
            if model.is_predefined:
                return jsonify({'message': '不能删除预定义模型'}), 403

        # 检查是否有任务正在使用此模型
        active_tasks = Task.query.filter_by(model_id=model_id).filter(
            Task.status.in_(['pending', 'queued', 'running'])
        ).count()

        if active_tasks > 0:
            return jsonify({'message': f'该模型有{active_tasks}个活跃任务，无法删除'}), 409

        # 管理员也不能删除预定义模型
        if model.is_predefined and not current_user.is_admin():
            return jsonify({'message': '不能删除预定义模型'}), 403

        db.session.delete(model)
        db.session.commit()

        return jsonify({'message': '模型删除成功'}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'删除模型错误: {str(e)}')
        return jsonify({'message': '删除模型失败，请稍后重试'}), 500


# ===== 数据集管理功能 =====

@admin_bp.route('/datasets', methods=['GET'])
@token_required
def get_all_datasets(current_user):
    """获取数据集列表（用户只能看到自己的，管理员可以看到所有）"""
    try:
        from app.models.db_datasets import Dataset

        # 解析查询参数
        task_type = request.args.get('task_type')
        status = request.args.get('status')
        source = request.args.get('source')

        query = Dataset.query

        # 权限检查：普通用户只能看到自己的数据集和官方数据集
        if not current_user.is_admin():
            query = query.filter(
                (Dataset.user_id == current_user.id) |
                (Dataset.source == 'official') |
                (Dataset.is_predefined == True)
            )

        # 应用筛选条件
        if task_type:
            query = query.filter_by(task_type=task_type)
        if status:
            query = query.filter_by(status=status)
        if source:
            query = query.filter_by(source=source)

        datasets = query.order_by(Dataset.created_at.desc()).all()
        datasets_data = [dataset.to_dict() for dataset in datasets]

        return jsonify({
            'datasets': datasets_data,
            'total': len(datasets_data)
        }), 200

    except Exception as e:
        current_app.logger.error(f'获取数据集列表错误: {str(e)}')
        return jsonify({'message': '获取数据集列表失败'}), 500


@admin_bp.route('/datasets', methods=['POST'])
@token_required
def create_dataset(current_user):
    """创建新数据集（用户创建自己的数据集）"""
    try:
        from app.models.db_datasets import Dataset

        data = request.get_json()

        if not data:
            return jsonify({'message': '请求数据不能为空'}), 400

        required_fields = ['dataset_name', 'task_type', 'dataset_path']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'message': f'{field}不能为空'}), 400

        # 检查数据集名称是否已存在
        if Dataset.query.filter_by(dataset_name=data['dataset_name']).first():
            return jsonify({'message': '数据集名称已存在'}), 409

        # 创建新数据集，设置用户ID
        new_dataset = Dataset(
            dataset_name=data['dataset_name'],
            task_type=data['task_type'],
            description=data.get('description', ''),
            dataset_path=data['dataset_path'],
            file_count=data.get('file_count', 0),
            file_types=data.get('file_types', []),
            total_size=data.get('total_size', 0),
            source='user',  # 用户上传的数据集
            status=data.get('status', 'available'),
            is_predefined=False,  # 用户上传的数据集不是预定义的
            user_id=current_user.id  # 设置创建者
        )

        db.session.add(new_dataset)
        db.session.commit()

        return jsonify({
            'message': '数据集创建成功',
            'dataset': new_dataset.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'创建数据集错误: {str(e)}')
        return jsonify({'message': '创建数据集失败，请稍后重试'}), 500


@admin_bp.route('/datasets/<int:dataset_id>', methods=['PUT'])
@token_required
def update_dataset(current_user, dataset_id):
    """更新数据集信息（用户只能更新自己的数据集，管理员可以更新所有）"""
    try:
        from app.models.db_datasets import Dataset

        dataset = Dataset.query.get(dataset_id)
        if not dataset:
            return jsonify({'message': '数据集不存在'}), 404

        # 权限检查：用户只能更新自己的数据集
        if not current_user.is_admin():
            if dataset.user_id != current_user.id:
                return jsonify({'message': '无权修改此数据集'}), 403
            if dataset.is_predefined:
                return jsonify({'message': '不能修改预定义数据集'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'message': '请求数据不能为空'}), 400

        # 更新允许的字段
        allowed_fields = [
            'dataset_name', 'task_type', 'description', 'dataset_path',
            'file_count', 'file_types', 'total_size', 'status'
        ]

        # 管理员可以修改所有字段，普通用户不能修改is_predefined和source
        if current_user.is_admin():
            allowed_fields.extend(['is_predefined', 'source'])

        for field in allowed_fields:
            if field in data:
                # 特殊处理数据集名称冲突检查
                if field == 'dataset_name' and data[field] != dataset.dataset_name:
                    if Dataset.query.filter_by(dataset_name=data[field]).first():
                        return jsonify({'message': '数据集名称已被其他数据集使用'}), 409
                setattr(dataset, field, data[field])

        db.session.commit()

        return jsonify({
            'message': '数据集信息更新成功',
            'dataset': dataset.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'更新数据集错误: {str(e)}')
        return jsonify({'message': '更新数据集失败，请稍后重试'}), 500


@admin_bp.route('/datasets/<int:dataset_id>', methods=['DELETE'])
@token_required
def delete_dataset(current_user, dataset_id):
    """删除数据集（用户只能删除自己的数据集，管理员可以删除所有）"""
    try:
        from app.models.db_datasets import Dataset
        from app.models.db_tasks import Task

        dataset = Dataset.query.get(dataset_id)
        if not dataset:
            return jsonify({'message': '数据集不存在'}), 404

        # 权限检查
        if not current_user.is_admin():
            if dataset.user_id != current_user.id:
                return jsonify({'message': '无权删除此数据集'}), 403
            if dataset.is_predefined:
                return jsonify({'message': '不能删除预定义数据集'}), 403

        # 检查是否有任务正在使用此数据集
        active_tasks = Task.query.filter_by(dataset_name=dataset.dataset_name).filter(
            Task.status.in_(['pending', 'queued', 'running'])
        ).count()

        if active_tasks > 0:
            return jsonify({'message': f'该数据集有{active_tasks}个活跃任务正在使用，无法删除'}), 409

        # 管理员也不能删除预定义数据集
        if dataset.is_predefined and not current_user.is_admin():
            return jsonify({'message': '不能删除预定义数据集'}), 403

        db.session.delete(dataset)
        db.session.commit()

        return jsonify({'message': '数据集删除成功'}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'删除数据集错误: {str(e)}')
        return jsonify({'message': '删除数据集失败，请稍后重试'}), 500


# ===== 攻击方式管理功能 =====

@admin_bp.route('/attack-methods', methods=['GET'])
@admin_required
def get_attack_methods(current_user):
    """获取支持的攻击方法列表（管理员功能）"""
    try:
        from app.attacks import get_supported_attacks, get_attack_descriptions

        methods = get_supported_attacks()
        descriptions = get_attack_descriptions()

        methods_data = []
        for method in methods:
            methods_data.append({
                'method': method,
                'name': descriptions.get(method, {}).get('name', method),
                'description': descriptions.get(method, {}).get('description', ''),
                'category': descriptions.get(method, {}).get('category', 'general')
            })

        return jsonify({
            'attack_methods': methods_data,
            'total': len(methods_data)
        }), 200

    except Exception as e:
        current_app.logger.error(f'获取攻击方法列表错误: {str(e)}')
        return jsonify({'message': '获取攻击方法列表失败'}), 500


@admin_bp.route('/attack-methods/<method_name>', methods=['GET'])
@admin_required
def get_attack_method_details(current_user, method_name):
    """获取特定攻击方法的详细信息（管理员功能）"""
    try:
        from app.attacks import get_supported_attacks, get_attack_descriptions

        methods = get_supported_attacks()
        if method_name not in methods:
            return jsonify({'message': '攻击方法不存在'}), 404

        descriptions = get_attack_descriptions()
        method_info = descriptions.get(method_name, {})

        # 获取使用此方法的统计信息
        from app.models.db_tasks import Task
        total_tasks = Task.query.filter_by(sub_task_type=method_name).count()
        successful_tasks = Task.query.filter_by(sub_task_type=method_name, status='completed').count()
        failed_tasks = Task.query.filter_by(sub_task_type=method_name, status='failed').count()

        method_details = {
            'method': method_name,
            'name': method_info.get('name', method_name),
            'description': method_info.get('description', ''),
            'category': method_info.get('category', 'general'),
            'parameters': method_info.get('parameters', {}),
            'statistics': {
                'total_tasks': total_tasks,
                'successful_tasks': successful_tasks,
                'failed_tasks': failed_tasks,
                'success_rate': round(successful_tasks / total_tasks * 100, 2) if total_tasks > 0 else 0
            }
        }

        return jsonify({
            'attack_method': method_details
        }), 200

    except Exception as e:
        current_app.logger.error(f'获取攻击方法详情错误: {str(e)}')
        return jsonify({'message': '获取攻击方法详情失败'}), 500
