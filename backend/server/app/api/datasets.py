from flask import Blueprint, request, jsonify
from app.services.dataset_service import DatasetService
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('datasets', __name__)

# 初始化数据集服务
dataset_service = DatasetService()

@bp.route('/datasets', methods=['GET'])
def get_datasets():
    """获取数据集列表"""
    try:
        task_type = request.args.get('task_type')  # 可选：按任务类型筛选
        
        if task_type:
            datasets = dataset_service.get_datasets_by_task_type(task_type)
        else:
            datasets = dataset_service.get_all_datasets()
        
        return jsonify({
            'success': True,
            'data': datasets
        }), 200
    except Exception as e:
        logger.error(f"获取数据集列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/datasets/<dataset_id>', methods=['GET'])
def get_dataset(dataset_id):
    """获取单个数据集详情"""
    try:
        dataset = dataset_service.get_dataset(int(dataset_id))
        return jsonify({
            'success': True,
            'data': [dataset]
        }), 200
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404
    except Exception as e:
        logger.error(f"获取数据集详情失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/datasets', methods=['POST'])
def add_dataset():
    """添加新数据集（手动）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求体不能为空'}), 400
        
        dataset_id = dataset_service.add_dataset(data)
        
        return jsonify({
            'success': True,
            'message': '数据集添加成功',
            'dataset_id': dataset_id
        }), 201
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"添加数据集失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/datasets/<int:dataset_id>', methods=['DELETE'])
def delete_dataset(dataset_id):
    """删除数据集"""
    try:
        success = dataset_service.delete_dataset(dataset_id)
        if success:
            return jsonify({
                'success': True,
                'message': '数据集删除成功'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': '数据集不存在'
            }), 404
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"删除数据集失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/datasets/upload', methods=['POST'])
def upload_dataset():
    """
    上传数据集文件
    
    支持两种上传方式（multipart/form-data格式）：
    
    【方式1：压缩包上传（推荐）】
    - dataset_name: 数据集名称（必需）
    - task_type: 任务类型（必需）
    - archive_file: 压缩包文件（zip/tar/tar.gz），包含所有数据集文件（推荐）
    - description: 数据集描述（可选）
    
    【方式2：多文件上传】
    - dataset_name: 数据集名称（必需）
    - task_type: 任务类型（必需）
    - files: 数据集文件（可多个，支持 jsonl, json, txt, csv, tsv）
    - description: 数据集描述（可选）
    
    注意：如果同时提供 archive_file 和其他文件，优先使用压缩包方式
    """
    try:
        # 获取表单数据
        dataset_name = request.form.get('dataset_name')
        task_type = request.form.get('task_type')
        description = request.form.get('description')
        
        if not dataset_name or not task_type:
            return jsonify({
                'success': False,
                'error': '缺少必需参数: dataset_name, task_type'
            }), 400
        
        # 获取文件
        # 方式1: 压缩包上传（推荐，更便捷）
        archive_file = request.files.get('archive_file')
        
        # 方式2: 多文件上传（兼容旧方式）
        files = request.files.getlist('files')
        
        # 如果提供了压缩包，优先使用压缩包方式
        if archive_file:
            upload_result = dataset_service.upload_dataset_files(
                dataset_name=dataset_name,
                task_type=task_type,
                archive_file=archive_file
            )
        else:
            # 否则使用多文件上传方式
            upload_result = dataset_service.upload_dataset_files(
                dataset_name=dataset_name,
                task_type=task_type,
                files=files if files else None
            )
        
        if not upload_result['success']:
            return jsonify(upload_result), 400
        
        # 保存到数据库
        dataset_id = dataset_service.save_uploaded_dataset_to_database(
            dataset_name=dataset_name,
            task_type=task_type,
            dataset_path=upload_result['dataset_dir'],
            file_count=upload_result['file_count'],
            file_types=upload_result['file_types'],
            total_size=upload_result['total_size'],
            description=description,
            source='user'
        )
        
        return jsonify({
            'success': True,
            'message': '数据集上传成功',
            'dataset_id': dataset_id,
            'upload_result': upload_result
        }), 201
    
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"上传数据集失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

