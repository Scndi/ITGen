import os
import shutil
import zipfile
import tarfile
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from app.models.db_models import Model as DBModel
from app.config import Config
from app.extensions import db
import logging

logger = logging.getLogger(__name__)

class ModelService:
    """模型服务类 - 统一管理模型CRUD和文件上传"""
    
    def __init__(self):
        """初始化模型服务"""
        self.base_dir = Config.BASE_DIR
        
        # 统一存储到 saved_models 目录（不再按任务类型分类）
        self.models_dir = Config.MODELS_BASE_DIR
        self.checkpoints_dir = Config.CHECKPOINTS_BASE_DIR
        
        # 初始化目录
        self._init_directories()
    
    def _init_directories(self):
        """初始化模型存储目录"""
        self.models_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"✓ 初始化模型目录: {self.models_dir}")
        
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"✓ 初始化检查点目录: {self.checkpoints_dir}")
    
    def get_all_models(self) -> List[Dict[str, Any]]:
        """获取所有模型"""
        db_models = DBModel.query.all()
        return [model.to_dict() for model in db_models]
    
    def get_model(self, model_id: int) -> Dict[str, Any]:
        """获取指定模型"""
        db_model = DBModel.query.filter_by(id=model_id).first()
        if not db_model:
            raise ValueError(f'模型 {model_id} 不存在')
        return db_model.to_dict()
    
    def add_model(self, model_data: Dict[str, Any]) -> int:
        """添加模型，返回新创建的模型ID"""
        # 检查是否已存在（通过model_name检查）
        model_name = model_data.get('model_name')
        if not model_name:
            raise ValueError('模型名称不能为空')
        
        existing_model = DBModel.query.filter_by(model_name=model_name).first()
        if existing_model:
            raise ValueError(f'模型名称 {model_name} 已存在')
        
        try:
            # 创建数据库模型（不指定id，由数据库自动生成）
            db_model = DBModel(
                model_name=model_data.get('model_name'),
                model_type=model_data.get('model_type'),
                description=model_data.get('description'),
                model_path=model_data.get('model_path'),
                tokenizer_path=model_data.get('tokenizer_path'),
                mlm_model_path=model_data.get('mlm_model_path'),
                checkpoint_path=model_data.get('checkpoint_path'),
                model_source=model_data.get('model_source', 'official'),
                max_length=model_data.get('max_length', 512),
                status='available',
                supported_tasks=model_data.get('supported_tasks', []),
                is_predefined=False
            )
            db.session.add(db_model)
            db.session.flush()  # 获取自增ID
            
            db.session.commit()
            logger.info(f"添加模型: ID={db_model.id}, model_name={model_name}, source={model_data.get('model_source', 'official')}")
            return db_model.id  # 返回自增ID
        except Exception as e:
            db.session.rollback()
            raise ValueError(f"添加模型失败: {str(e)}")
    
    def delete_model(self, model_id: int) -> bool:
        """
        删除模型（包括文件和数据库记录）
        
        Args:
            model_id: 模型ID
            
        Returns:
            是否删除成功
        """
        db_model = DBModel.query.filter_by(id=model_id).first()
        if not db_model:
            return False
        
        if db_model.is_predefined:
            raise ValueError('不能删除预定义模型')
        
        try:
            # 如果是用户上传的模型，删除文件
            if db_model.model_source == 'user':
                # 删除模型文件（可能是文件或目录）
                if db_model.model_path and os.path.exists(db_model.model_path):
                    if os.path.isfile(db_model.model_path):
                        os.remove(db_model.model_path)
                        logger.info(f"✓ 删除模型文件: {db_model.model_path}")
                    elif os.path.isdir(db_model.model_path):
                        # 如果是目录，删除整个目录（包括其中的所有文件）
                        shutil.rmtree(db_model.model_path)
                        logger.info(f"✓ 删除模型目录: {db_model.model_path}")
                
                # 删除 MLM 模型文件（如果存在）
                if db_model.mlm_model_path and os.path.exists(db_model.mlm_model_path):
                    if os.path.isfile(db_model.mlm_model_path):
                        os.remove(db_model.mlm_model_path)
                        logger.info(f"✓ 删除 MLM 模型文件: {db_model.mlm_model_path}")
                    elif os.path.isdir(db_model.mlm_model_path):
                        # 如果是目录，删除整个 MLM 目录
                        shutil.rmtree(db_model.mlm_model_path)
                        logger.info(f"✓ 删除 MLM 模型目录: {db_model.mlm_model_path}")
                
                # 如果 model_path 是目录，检查其中是否有 mlm 子目录（兼容旧存储方式）
                if db_model.model_path and os.path.isdir(db_model.model_path):
                    mlm_subdir = Path(db_model.model_path) / 'mlm'
                    if mlm_subdir.exists() and mlm_subdir.is_dir():
                        shutil.rmtree(mlm_subdir)
                        logger.info(f"✓ 删除 MLM 子目录: {mlm_subdir}")
                
                # 删除检查点文件
                if db_model.checkpoint_path and os.path.exists(db_model.checkpoint_path):
                    if os.path.isfile(db_model.checkpoint_path):
                        os.remove(db_model.checkpoint_path)
                        logger.info(f"✓ 删除检查点文件: {db_model.checkpoint_path}")
                    elif os.path.isdir(db_model.checkpoint_path):
                        shutil.rmtree(db_model.checkpoint_path)
                        logger.info(f"✓ 删除检查点目录: {db_model.checkpoint_path}")
            
            # 删除数据库记录
            db.session.delete(db_model)
            db.session.commit()
            logger.info(f"✓ 模型删除成功: ID={model_id}")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"✗ 删除模型失败: {str(e)}")
            raise ValueError(f"删除模型失败: {str(e)}")
    
    def test_model(self, model_id: int, task_type: str, code1: str, code2: str) -> Dict[str, Any]:
        """测试模型"""
        db_model = DBModel.query.filter_by(id=model_id).first()
        if not db_model:
            raise ValueError(f'模型 {model_id} 不存在')

        # 检查输入参数
        if not code1:
            return {
                'model_id': model_id,
                'task_type': task_type,
                'success': False,
                'error': 'code1不能为空',
                'note': '输入验证失败'
            }

        # 这里应该调用实际的模型推理
        # 如果模型文件不存在，返回错误
        model_path = db_model.model_path
        if not model_path or not os.path.exists(model_path):
            return {
                'model_id': model_id,
                'task_type': task_type,
                'success': False,
                'error': f'模型文件不存在: {model_path}',
                'note': '需要先上传或训练模型'
            }

        # 尝试加载和测试模型
        try:
            # 这里应该实现实际的模型推理逻辑
            # 目前返回错误，表明需要实现
            return {
                'model_id': model_id,
                'task_type': task_type,
                'success': False,
                'error': '模型推理逻辑尚未实现',
                'note': '需要实现真实的模型推理算法',
                'code1': code1,
                'code2': code2
            }
        except Exception as e:
            return {
                'model_id': model_id,
                'task_type': task_type,
                'success': False,
                'error': f'模型推理失败: {str(e)}',
                'note': '模型推理过程中发生错误',
                'code1': code1,
                'code2': code2
            }
    
    # ==================== 模型文件上传相关方法 ====================
    
    def _get_model_storage_path(self, model_name: str) -> Path:
        """
        获取模型存储路径（统一存储到 saved_models 目录）
        
        Args:
            model_name: 模型名称
            
        Returns:
            模型存储目录路径
        """
        model_dir = self.models_dir / secure_filename(model_name)
        model_dir.mkdir(parents=True, exist_ok=True)
        
        return model_dir
    
    def _get_checkpoint_storage_path(self, model_name: str) -> Path:
        """
        获取检查点存储路径（统一存储到 checkpoints 目录）
        
        Args:
            model_name: 模型名称
            
        Returns:
            检查点存储目录路径
        """
        checkpoint_dir = self.checkpoints_dir / secure_filename(model_name)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        return checkpoint_dir
    
    def upload_model_files(
        self,
        model_name: str,
        archive_file: FileStorage
    ) -> Dict[str, Any]:
        """
        上传模型文件（仅支持压缩包上传）
        
        Args:
            model_name: 模型名称
            archive_file: 压缩包文件（zip/tar/tar.gz），包含模型和tokenizer文件（不包含MLM）
            
        Returns:
            上传结果字典
        """
        try:
            # 获取存储路径（统一存储到 saved_models 目录）
            model_dir = self._get_model_storage_path(model_name)
            
            # 处理压缩包
            return self._extract_and_organize_archive(
                archive_file, model_name, model_dir
            )
        
        except Exception as e:
            logger.error(f"✗ 模型文件上传失败: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def upload_mlm_model(
        self,
        model_name: str,
        mlm_archive_file: FileStorage
    ) -> Dict[str, Any]:
        """
        上传MLM模型文件（单独上传）
        
        Args:
            model_name: 模型名称（必须已存在）
            mlm_archive_file: MLM模型压缩包文件（zip/tar/tar.gz）
            
        Returns:
            上传结果字典
        """
        try:
            # 检查模型是否存在
            db_model = DBModel.query.filter_by(model_name=model_name).first()
            if not db_model:
                raise ValueError(f'模型 {model_name} 不存在，请先上传主模型')
            
            # 获取模型目录
            model_dir = self._get_model_storage_path(model_name)
            mlm_dir = model_dir / 'mlm'
            mlm_dir.mkdir(parents=True, exist_ok=True)
            
            # 解压MLM模型
            archive_filename = secure_filename(mlm_archive_file.filename)
            archive_ext = archive_filename.rsplit('.', 1)[-1].lower() if '.' in archive_filename else ''
            
            # 创建临时目录
            temp_dir = mlm_dir / '.temp_extract'
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存压缩包到临时目录
            archive_path = temp_dir / archive_filename
            mlm_archive_file.save(str(archive_path))
            
            # 解压压缩包
            extract_dir = temp_dir / 'extracted'
            extract_dir.mkdir(parents=True, exist_ok=True)
            
            if archive_ext in ['zip']:
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            elif archive_ext in ['tar', 'gz']:
                mode = 'r:gz' if archive_ext == 'gz' else 'r'
                with tarfile.open(archive_path, mode) as tar_ref:
                    tar_ref.extractall(extract_dir)
            else:
                raise ValueError(f"不支持的压缩包格式: {archive_ext}。支持的格式: zip, tar, tar.gz")
            
            logger.info(f"✓ MLM压缩包解压成功: {archive_filename}")
            
            # 移动所有文件到mlm目录
            for item in extract_dir.rglob('*'):
                if item.is_file():
                    target_path = mlm_dir / item.name
                    shutil.move(str(item), str(target_path))
                    logger.info(f"✓ 移动MLM文件: {target_path}")
            
            # 清理临时目录
            shutil.rmtree(temp_dir)
            
            # 更新数据库中的mlm_model_path
            mlm_model_path = str(mlm_dir)
            db_model.mlm_model_path = mlm_model_path
            db.session.commit()
            
            logger.info(f"✓ MLM模型上传成功: {mlm_model_path}")
            
            return {
                'success': True,
                'model_name': model_name,
                'mlm_model_path': mlm_model_path
            }
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"✗ MLM模型上传失败: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def save_uploaded_model_to_database(
        self,
        model_name: str,
        model_type: str,
        task_type: str,
        model_path: str,
        tokenizer_path: str,
        mlm_model_path: Optional[str] = None,
        checkpoint_path: Optional[str] = None,
        description: Optional[str] = None,
        model_source: str = 'user'
    ) -> int:
        """
        保存上传的模型信息到数据库
        
        Args:
            model_name: 模型名称
            model_type: 模型类型（roberta, gpt2等）
            task_type: 任务类型
            model_path: 模型路径（本地路径或HuggingFace路径）
            tokenizer_path: Tokenizer路径
            mlm_model_path: MLM模型路径（可选）
            checkpoint_path: 检查点路径（可选）
            description: 模型描述（可选）
            model_source: 模型来源（official/user）
            
        Returns:
            模型ID
        """
        try:
            # 检查是否已存在
            existing_model = DBModel.query.filter_by(model_name=model_name).first()
            if existing_model:
                raise ValueError(f'模型名称 {model_name} 已存在')
            
            # 创建数据库记录
            # 将task_type保存到supported_tasks中
            supported_tasks = [task_type] if task_type else []
            
            db_model = DBModel(
                model_name=model_name,
                model_type=model_type,
                description=description,
                model_path=model_path,
                tokenizer_path=tokenizer_path,
                mlm_model_path=mlm_model_path,
                checkpoint_path=checkpoint_path,
                model_source=model_source,
                max_length=512,
                status='available',
                supported_tasks=supported_tasks,
                is_predefined=False
            )
            
            db.session.add(db_model)
            db.session.flush()
            model_id = db_model.id
            db.session.commit()
            
            logger.info(f"✓ 模型信息保存到数据库: ID={model_id}, model_name={model_name}")
            return model_id
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"✗ 保存模型信息失败: {str(e)}")
            raise
    
    def _extract_and_organize_archive(
        self,
        archive_file: FileStorage,
        model_name: str,
        model_dir: Path
    ) -> Dict[str, Any]:
        """
        解压压缩包并自动组织文件
        
        Args:
            archive_file: 压缩包文件
            model_name: 模型名称
            model_dir: 模型存储目录
            
        Returns:
            上传结果字典
        """
        try:
            archive_filename = secure_filename(archive_file.filename)
            archive_ext = archive_filename.rsplit('.', 1)[-1].lower() if '.' in archive_filename else ''
            
            # 创建临时目录
            temp_dir = model_dir / '.temp_extract'
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存压缩包到临时目录
            archive_path = temp_dir / archive_filename
            archive_file.save(str(archive_path))
            
            # 解压压缩包
            extract_dir = temp_dir / 'extracted'
            extract_dir.mkdir(parents=True, exist_ok=True)
            
            if archive_ext in ['zip']:
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            elif archive_ext in ['tar', 'gz']:
                mode = 'r:gz' if archive_ext == 'gz' else 'r'
                with tarfile.open(archive_path, mode) as tar_ref:
                    tar_ref.extractall(extract_dir)
            else:
                raise ValueError(f"不支持的压缩包格式: {archive_ext}。支持的格式: zip, tar, tar.gz")
            
            logger.info(f"✓ 压缩包解压成功: {archive_filename}")
            
            # 自动识别和组织文件
            uploaded_files = {}
            
            # 查找模型文件
            model_patterns = ['*.bin', '*.pth', '*.pt', '*.ckpt', 'pytorch_model.bin', 'model.bin']
            for pattern in model_patterns:
                model_files = list(extract_dir.rglob(pattern))
                if model_files:
                    model_file = model_files[0]  # 取第一个
                    target_path = model_dir / model_file.name
                    shutil.move(str(model_file), str(target_path))
                    uploaded_files['model_path'] = str(target_path)
                    logger.info(f"✓ 找到并移动模型文件: {target_path}")
                    break
            
            # 查找Tokenizer文件
            tokenizer_patterns = ['tokenizer.json', 'vocab.json', 'vocab.txt', 'merges.txt', 'tokenizer_config.json']
            tokenizer_files_found = []
            for pattern in tokenizer_patterns:
                tokenizer_files = list(extract_dir.rglob(pattern))
                for tokenizer_file in tokenizer_files:
                    target_path = model_dir / tokenizer_file.name
                    shutil.move(str(tokenizer_file), str(target_path))
                    tokenizer_files_found.append(str(target_path))
                    logger.info(f"✓ 找到并移动Tokenizer文件: {target_path}")
            
            if tokenizer_files_found:
                uploaded_files['tokenizer_path'] = str(model_dir)
                uploaded_files['tokenizer_files'] = tokenizer_files_found
            
            # 查找配置文件
            config_patterns = ['config.json', '*.config']
            for pattern in config_patterns:
                config_files = list(extract_dir.rglob(pattern))
                for config_file in config_files:
                    target_path = model_dir / config_file.name
                    shutil.move(str(config_file), str(target_path))
                    logger.info(f"✓ 找到并移动配置文件: {target_path}")
            
            # 注意：MLM模型文件不在这里处理，需要单独通过 upload_mlm_model 上传
            
            # 查找检查点文件（如果有，放在模型目录下）
            checkpoint_patterns = ['checkpoint*.bin', 'checkpoint*.pth', '*checkpoint*.pt']
            for pattern in checkpoint_patterns:
                checkpoint_files = list(extract_dir.rglob(pattern))
                if checkpoint_files:
                    checkpoint_file = checkpoint_files[0]
                    target_path = model_dir / checkpoint_file.name
                    shutil.move(str(checkpoint_file), str(target_path))
                    uploaded_files['checkpoint_path'] = str(target_path)
                    logger.info(f"✓ 找到并移动检查点文件: {target_path}")
                    break
            
            # 移动剩余文件到模型目录
            for item in extract_dir.rglob('*'):
                if item.is_file() and item not in [archive_path]:
                    target_path = model_dir / item.name
                    if not target_path.exists():
                        shutil.move(str(item), str(target_path))
                        logger.info(f"✓ 移动其他文件: {target_path}")
            
            # 清理临时目录
            shutil.rmtree(temp_dir)
            
            return {
                'success': True,
                'model_name': model_name,
                'model_dir': str(model_dir),
                'uploaded_files': uploaded_files,
                'extracted_from_archive': True
            }
        
        except Exception as e:
            logger.error(f"✗ 解压压缩包失败: {str(e)}", exc_info=True)
            # 清理临时目录
            if 'temp_dir' in locals() and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            return {
                'success': False,
                'error': f'解压压缩包失败: {str(e)}'
        }
