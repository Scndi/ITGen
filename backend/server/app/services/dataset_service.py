import os
import shutil
import zipfile
import tarfile
from typing import List, Dict, Any, Optional
from pathlib import Path
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from app.models.db_datasets import Dataset as DBDataset
from app.config import Config
from app.extensions import db
import logging

logger = logging.getLogger(__name__)

class DatasetService:
    """数据集服务类 - 统一管理数据集CRUD和文件上传"""
    
    # 允许的文件扩展名
    ALLOWED_EXTENSIONS = {
        'jsonl': ['.jsonl'],
        'json': ['.json'],
        'txt': ['.txt'],
        'csv': ['.csv'],
        'tsv': ['.tsv'],
    }
    
    def __init__(self):
        """初始化数据集服务"""
        self.base_dir = Config.BASE_DIR
        
        # 任务类型到存储目录的映射
        self.TASK_TYPE_DIRS = {
            'clone-detection': Config.DATASETS_CLONE_DETECTION,
            'vulnerability-prediction': Config.DATASETS_VULNERABILITY,
            'code-summarization': Config.DATASETS_CODE_SUMMARIZATION,
        }
        
        # 初始化目录
        self._init_directories()
    
    def _init_directories(self):
        """初始化数据集存储目录"""
        for task_type, dir_path in self.TASK_TYPE_DIRS.items():
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"✓ 初始化数据集目录: {dir_path}")
    
    def get_all_datasets(self) -> List[Dict[str, Any]]:
        """获取所有数据集"""
        db_datasets = DBDataset.query.all()
        return [dataset.to_dict() for dataset in db_datasets]
    
    def get_dataset(self, dataset_id: int) -> Dict[str, Any]:
        """获取指定数据集"""
        db_dataset = DBDataset.query.filter_by(id=dataset_id).first()
        if not db_dataset:
            raise ValueError(f'数据集 {dataset_id} 不存在')
        return db_dataset.to_dict()
    
    def get_datasets_by_task_type(self, task_type: str) -> List[Dict[str, Any]]:
        """根据任务类型获取数据集"""
        db_datasets = DBDataset.query.filter_by(task_type=task_type, status='available').all()
        return [dataset.to_dict() for dataset in db_datasets]
    
    def add_dataset(self, dataset_data: Dict[str, Any]) -> int:
        """添加数据集，返回新创建的数据集ID"""
        dataset_name = dataset_data.get('dataset_name')
        if not dataset_name:
            raise ValueError('数据集名称不能为空')
        
        existing_dataset = DBDataset.query.filter_by(dataset_name=dataset_name).first()
        if existing_dataset:
            raise ValueError(f'数据集名称 {dataset_name} 已存在')
        
        try:
            db_dataset = DBDataset(
                dataset_name=dataset_data.get('dataset_name'),
                task_type=dataset_data.get('task_type'),
                description=dataset_data.get('description'),
                dataset_path=dataset_data.get('dataset_path', ''),
                file_count=dataset_data.get('file_count', 0),
                file_types=dataset_data.get('file_types', []),
                total_size=dataset_data.get('total_size', 0),
                source=dataset_data.get('source', 'user'),
                status='available',
                is_predefined=False
            )
            db.session.add(db_dataset)
            db.session.flush()
            
            db.session.commit()
            logger.info(f"添加数据集: ID={db_dataset.id}, dataset_name={dataset_name}")
            return db_dataset.id
        except Exception as e:
            db.session.rollback()
            raise ValueError(f"添加数据集失败: {str(e)}")
    
    def delete_dataset(self, dataset_id: int) -> bool:
        """删除数据集（包括文件和数据库记录）"""
        db_dataset = DBDataset.query.filter_by(id=dataset_id).first()
        if not db_dataset:
            return False
        
        if db_dataset.is_predefined:
            raise ValueError('不能删除预定义数据集')
        
        try:
            # 如果是用户上传的数据集，删除文件
            if db_dataset.source == 'user' and db_dataset.dataset_path:
                dataset_path = Path(db_dataset.dataset_path)
                if dataset_path.exists():
                    if dataset_path.is_file():
                        os.remove(dataset_path)
                    elif dataset_path.is_dir():
                        shutil.rmtree(dataset_path)
                    logger.info(f"✓ 删除数据集文件: {dataset_path}")
            
            # 删除数据库记录
            db.session.delete(db_dataset)
            db.session.commit()
            logger.info(f"✓ 数据集删除成功: ID={dataset_id}")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"✗ 删除数据集失败: {str(e)}")
            raise ValueError(f"删除数据集失败: {str(e)}")
    
    def _get_dataset_storage_path(self, dataset_name: str, task_type: str) -> Path:
        """获取数据集存储路径"""
        if task_type not in self.TASK_TYPE_DIRS:
            raise ValueError(f"不支持的任务类型: {task_type}")
        
        base_dir = self.TASK_TYPE_DIRS[task_type]
        dataset_dir = base_dir / secure_filename(dataset_name)
        dataset_dir.mkdir(parents=True, exist_ok=True)
        
        return dataset_dir
    
    def _get_file_extension(self, filename: str) -> str:
        """获取文件扩展名（不含点）"""
        return Path(filename).suffix.lower().lstrip('.')
    
    def _is_allowed_file(self, filename: str) -> bool:
        """检查文件扩展名是否允许"""
        ext = self._get_file_extension(filename)
        for allowed_exts in self.ALLOWED_EXTENSIONS.values():
            if f'.{ext}' in allowed_exts:
                return True
        return False
    
    def upload_dataset_files(
        self,
        dataset_name: str,
        task_type: str,
        files: Optional[List[FileStorage]] = None,
        archive_file: Optional[FileStorage] = None
    ) -> Dict[str, Any]:
        """
        上传数据集文件
        
        支持两种方式：
        1. 多文件上传：分别上传多个文件
        2. 压缩包上传：上传一个压缩包（zip/tar/tar.gz），自动解压
        
        Args:
            dataset_name: 数据集名称
            task_type: 任务类型
            files: 文件列表（多文件上传）
            archive_file: 压缩包文件（压缩包上传）
            
        Returns:
            上传结果字典
        """
        try:
            # 获取存储路径
            dataset_dir = self._get_dataset_storage_path(dataset_name, task_type)
            
            uploaded_files = []
            file_types = set()
            total_size = 0
            
            # 如果提供了压缩包，优先处理压缩包
            if archive_file:
                return self._extract_and_organize_archive(
                    archive_file, dataset_name, task_type, dataset_dir
                )
            
            # 多文件上传
            if not files:
                raise ValueError('必须提供文件或压缩包')
            
            for file in files:
                if not file or not file.filename:
                    continue
                
                if not self._is_allowed_file(file.filename):
                    logger.warning(f"跳过不支持的文件类型: {file.filename}")
                    continue
                
                filename = secure_filename(file.filename)
                file_path = dataset_dir / filename
                file.save(str(file_path))
                
                file_size = file_path.stat().st_size
                file_ext = self._get_file_extension(filename)
                
                uploaded_files.append({
                    'filename': filename,
                    'path': str(file_path),
                    'size': file_size,
                    'type': file_ext
                })
                file_types.add(file_ext)
                total_size += file_size
                
                logger.info(f"✓ 文件上传成功: {file_path} ({file_size} bytes)")
            
            return {
                'success': True,
                'dataset_name': dataset_name,
                'task_type': task_type,
                'dataset_dir': str(dataset_dir),
                'uploaded_files': uploaded_files,
                'file_count': len(uploaded_files),
                'file_types': list(file_types),
                'total_size': total_size
            }
        
        except Exception as e:
            logger.error(f"✗ 数据集文件上传失败: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_and_organize_archive(
        self,
        archive_file: FileStorage,
        dataset_name: str,
        task_type: str,
        dataset_dir: Path
    ) -> Dict[str, Any]:
        """解压压缩包并自动组织文件"""
        try:
            archive_filename = secure_filename(archive_file.filename)
            archive_ext = archive_filename.rsplit('.', 1)[-1].lower() if '.' in archive_filename else ''
            
            # 创建临时目录
            temp_dir = dataset_dir / '.temp_extract'
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
            
            # 移动文件到数据集目录
            uploaded_files = []
            file_types = set()
            total_size = 0
            
            for item in extract_dir.rglob('*'):
                if item.is_file():
                    filename = item.name
                    if self._is_allowed_file(filename):
                        target_path = dataset_dir / filename
                        # 如果文件已存在，添加序号
                        if target_path.exists():
                            base_name = target_path.stem
                            ext = target_path.suffix
                            counter = 1
                            while target_path.exists():
                                target_path = dataset_dir / f"{base_name}_{counter}{ext}"
                                counter += 1
                        
                        shutil.move(str(item), str(target_path))
                        file_size = target_path.stat().st_size
                        file_ext = self._get_file_extension(filename)
                        
                        uploaded_files.append({
                            'filename': filename,
                            'path': str(target_path),
                            'size': file_size,
                            'type': file_ext
                        })
                        file_types.add(file_ext)
                        total_size += file_size
                        
                        logger.info(f"✓ 移动文件: {target_path}")
            
            # 清理临时目录
            shutil.rmtree(temp_dir)
            
            return {
                'success': True,
                'dataset_name': dataset_name,
                'task_type': task_type,
                'dataset_dir': str(dataset_dir),
                'uploaded_files': uploaded_files,
                'file_count': len(uploaded_files),
                'file_types': list(file_types),
                'total_size': total_size,
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
    
    def save_uploaded_dataset_to_database(
        self,
        dataset_name: str,
        task_type: str,
        dataset_path: str,
        file_count: int,
        file_types: List[str],
        total_size: int,
        description: Optional[str] = None,
        source: str = 'user'
    ) -> int:
        """保存上传的数据集信息到数据库"""
        try:
            existing_dataset = DBDataset.query.filter_by(dataset_name=dataset_name).first()
            if existing_dataset:
                raise ValueError(f'数据集名称 {dataset_name} 已存在')
            
            db_dataset = DBDataset(
                dataset_name=dataset_name,
                task_type=task_type,
                description=description,
                dataset_path=dataset_path,
                file_count=file_count,
                file_types=file_types,
                total_size=total_size,
                source=source,
                status='available',
                is_predefined=False
            )
            
            db.session.add(db_dataset)
            db.session.flush()
            dataset_id = db_dataset.id
            db.session.commit()
            
            logger.info(f"✓ 数据集信息保存到数据库: ID={dataset_id}, dataset_name={dataset_name}")
            return dataset_id
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"✗ 保存数据集信息失败: {str(e)}")
            raise

