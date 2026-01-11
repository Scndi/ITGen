"""用户认证控制器"""
import jwt
import datetime
from flask import Blueprint, request, jsonify, current_app
from app.models.db_users import User
from app.extensions import db

auth_bp = Blueprint('auth', __name__)

def create_token(user_id):
    """创建JWT token"""
    payload = {
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1),  # 1天过期
        'iat': datetime.datetime.utcnow()
    }
    token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
    return token

def token_required(f):
    """JWT token验证装饰器"""
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': '缺少认证token'}), 401

        try:
            # 移除Bearer前缀
            if token.startswith('Bearer '):
                token = token[7:]

            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.get(payload['user_id'])
            if not current_user:
                return jsonify({'message': '用户不存在'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'token已过期'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': '无效的token'}), 401

        return f(current_user, *args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated

@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.get_json()

        if not data or not data.get('username') or not data.get('password'):
            return jsonify({'message': '用户名和密码不能为空'}), 400

        username = data['username']
        password = data['password']

        # 查找用户（支持用户名或邮箱登录）
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()

        if not user:
            return jsonify({'message': '用户不存在'}), 401

        if not user.is_active():
            return jsonify({'message': '账户已被禁用'}), 401

        if not user.check_password(password):
            user.increment_login_attempts()
            db.session.commit()

            if user.login_attempts >= 5:
                user.lock_account()
                db.session.commit()
                return jsonify({'message': '密码错误次数过多，账户已被锁定30分钟'}), 401

            return jsonify({'message': '用户名或密码错误'}), 401

        # 登录成功，重置失败次数并更新最后登录时间
        user.reset_login_attempts()
        user.update_last_login()
        db.session.commit()

        # 创建token
        token = create_token(user.id)

        return jsonify({
            'message': '登录成功',
            'token': token,
            'user': user.to_safe_dict()
        }), 200

    except Exception as e:
        current_app.logger.error(f'登录错误: {str(e)}')
        return jsonify({'message': '登录失败，请稍后重试'}), 500

@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'message': '请求数据不能为空'}), 400

        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'message': f'{field}不能为空'}), 400

        username = data['username']
        email = data['email']
        password = data['password']

        # 验证用户名长度
        if len(username) < 3 or len(username) > 20:
            return jsonify({'message': '用户名长度必须在3-20个字符之间'}), 400

        # 验证用户名格式（只允许字母、数字、下划线）
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return jsonify({'message': '用户名只能包含字母、数字和下划线'}), 400

        # 验证邮箱格式
        import re as email_re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not email_re.match(email_pattern, email):
            return jsonify({'message': '请输入有效的邮箱地址'}), 400

        # 验证密码强度
        if len(password) < 6:
            return jsonify({'message': '密码长度至少6位'}), 400

        # 验证full_name长度（如果提供）
        full_name = data.get('full_name', '')
        if full_name and (len(full_name) < 1 or len(full_name) > 100):
            return jsonify({'message': '真实姓名长度必须在1-100个字符之间'}), 400

        # 验证department长度（如果提供）
        department = data.get('department', '')
        if department and len(department) > 100:
            return jsonify({'message': '部门名称长度不能超过100个字符'}), 400

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
            role='user',  # 默认注册为普通用户
            status='active'
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        return jsonify({
            'message': '注册成功',
            'user': new_user.to_safe_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'注册错误: {str(e)}')
        return jsonify({'message': '注册失败，请稍后重试'}), 500

@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    """获取当前用户信息"""
    try:
        return jsonify({
            'user': current_user.to_safe_dict()
        }), 200

    except Exception as e:
        current_app.logger.error(f'获取用户信息错误: {str(e)}')
        return jsonify({'message': '获取用户信息失败'}), 500

@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    """用户登出"""
    try:
        # 在实际应用中，可以将token加入黑名单
        # 这里只是返回成功响应
        return jsonify({'message': '登出成功'}), 200

    except Exception as e:
        current_app.logger.error(f'登出错误: {str(e)}')
        return jsonify({'message': '登出失败'}), 500
