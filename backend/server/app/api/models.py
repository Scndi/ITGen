from flask import Blueprint, request, jsonify
from app.services.model_service import ModelService
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('models', __name__)

# 初始化模型服务
model_service = ModelService()

@bp.route('/models', methods=['GET'])
def get_models():
    """获取模型列表"""
    print("有请求进来了/models接口")
    try:
        models = model_service.get_all_models()
        return jsonify({
            'success': True,
            'data': models
        }), 200
    except Exception as e:
        logger.error(f"获取模型列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/models/<model_id>', methods=['GET'])
def get_model(model_id):
    """获取单个模型详情"""
    try:
        model = model_service.get_model(model_id)
        return jsonify({
            'success': True,
            'data': [model]
        }), 200
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404
    except Exception as e:
        logger.error(f"获取模型详情失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/models', methods=['POST'])
def add_model():
    """添加新模型"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求体不能为空'}), 400
        
        model_id = model_service.add_model(data)
        
        return jsonify({
            'success': True,
            'message': '模型添加成功',
            'model_id': model_id
        }), 201
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"添加模型失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/models/<int:model_id>', methods=['DELETE'])
def delete_model(model_id):
    """删除模型"""
    try:
        success = model_service.delete_model(model_id)
        if success:
            return jsonify({
                'success': True,
                'message': '模型删除成功'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': '模型不存在'
            }), 404
    except Exception as e:
        logger.error(f"删除模型失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/models/<int:model_id>/test', methods=['POST'])
def test_model(model_id):
    """测试模型"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求体不能为空'}), 400
        
        task_type = data.get('task_type')
        code1 = data.get('code1')
        code2 = data.get('code2')
        
        # 执行模型测试
        result = model_service.test_model(model_id, task_type, code1, code2)
        
        return jsonify({
            'success': True,
            'result': result
        }), 200
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"测试模型失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/models/upload', methods=['POST'])
def upload_model():
    """
    上传模型文件（仅支持压缩包上传）
    
    请求参数（multipart/form-data格式）：
    - model_name: 模型名称（必需）
    - task_type: 任务类型（必需）
    - model_type: 模型类型（如roberta，必需）
    - archive_file: 压缩包文件（zip/tar/tar.gz），包含模型和tokenizer文件（不包含MLM）
    - description: 模型描述（可选）
    
    注意：MLM模型需要单独通过 /models/upload/mlm 接口上传
    """
    try:
        # 获取表单数据
        model_name = request.form.get('model_name')
        task_type = request.form.get('task_type')
        model_type = request.form.get('model_type')
        description = request.form.get('description')
        
        if not model_name or not task_type or not model_type:
            return jsonify({
                'success': False,
                'error': '缺少必需参数: model_name, task_type, model_type'
            }), 400
        
        # 获取压缩包文件（必需）
        archive_file = request.files.get('archive_file')
        if not archive_file:
            return jsonify({
                'success': False,
                'error': '缺少必需文件: archive_file（压缩包）'
            }), 400
        
        # 上传模型文件（压缩包）
        upload_result = model_service.upload_model_files(
            model_name=model_name,
            archive_file=archive_file
        )
        
        if not upload_result['success']:
            return jsonify(upload_result), 400
        
        # 保存到数据库
        model_id = model_service.save_uploaded_model_to_database(
            model_name=model_name,
            model_type=model_type,
            task_type=task_type,
            model_path=upload_result['uploaded_files'].get('model_path', ''),
            tokenizer_path=upload_result['uploaded_files'].get('tokenizer_path', ''),
            mlm_model_path=None,  # MLM需要单独上传
            checkpoint_path=upload_result['uploaded_files'].get('checkpoint_path'),
            description=description,
            model_source='user'
        )
        
        return jsonify({
            'success': True,
            'message': '模型上传成功（MLM模型需要单独上传）',
            'model_id': model_id,
            'upload_result': upload_result
        }), 201
    
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"上传模型失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/models/upload/mlm', methods=['POST'])
def upload_mlm_model():
    """
    上传MLM模型文件（单独上传）
    
    请求参数（multipart/form-data格式）：
    - model_name: 模型名称（必需，必须已存在）
    - mlm_archive_file: MLM模型压缩包文件（zip/tar/tar.gz）
    
    注意：必须先通过 /models/upload 上传主模型
    """
    try:
        # 获取表单数据
        model_name = request.form.get('model_name')
        if not model_name:
            return jsonify({
                'success': False,
                'error': '缺少必需参数: model_name'
            }), 400
        
        # 获取MLM压缩包文件（必需）
        mlm_archive_file = request.files.get('mlm_archive_file')
        if not mlm_archive_file:
            return jsonify({
                'success': False,
                'error': '缺少必需文件: mlm_archive_file（MLM模型压缩包）'
            }), 400
        
        # 上传MLM模型
        upload_result = model_service.upload_mlm_model(
            model_name=model_name,
            mlm_archive_file=mlm_archive_file
        )
        
        if not upload_result['success']:
            return jsonify(upload_result), 400
        
        return jsonify({
            'success': True,
            'message': 'MLM模型上传成功',
            'upload_result': upload_result
        }), 201
    
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"上传MLM模型失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

