-- ITGen 数据库完整建表脚本
-- 包含所有表结构和初始数据
-- 执行顺序：先创建数据库，然后依次执行表创建和数据插入

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS itgen_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE itgen_db;

-- ===========================================
-- 用户表 (users)
-- ===========================================
CREATE TABLE IF NOT EXISTS `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '用户ID（自增）',
    `username` VARCHAR(100) NOT NULL UNIQUE COMMENT '用户名（唯一）',
    `email` VARCHAR(200) NOT NULL UNIQUE COMMENT '邮箱地址（唯一）',
    `password_hash` VARCHAR(256) NOT NULL COMMENT '密码哈希',
    `full_name` VARCHAR(200) COMMENT '真实姓名',
    `role` VARCHAR(50) DEFAULT 'user' COMMENT '用户角色: admin(管理员)/user(普通用户)',
    `status` VARCHAR(50) DEFAULT 'active' COMMENT '用户状态: active/inactive/suspended',
    `last_login` DATETIME COMMENT '最后登录时间',
    `login_attempts` INT DEFAULT 0 COMMENT '登录失败次数',
    `locked_until` DATETIME COMMENT '账户锁定截止时间',
    `email_verified` BOOLEAN DEFAULT FALSE COMMENT '邮箱是否验证',
    `phone` VARCHAR(20) COMMENT '手机号码',
    `department` VARCHAR(100) COMMENT '部门',
    `position` VARCHAR(100) COMMENT '职位',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_username` (`username`),
    INDEX `idx_email` (`email`),
    INDEX `idx_role` (`role`),
    INDEX `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ===========================================
-- 模型表 (models)
-- ===========================================
CREATE TABLE IF NOT EXISTS `models` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '模型ID（自增）',
    `model_name` VARCHAR(200) NOT NULL COMMENT '模型名称',
    `model_type` VARCHAR(100) NOT NULL COMMENT '模型类型',
    `description` TEXT COMMENT '模型描述',
    `model_path` VARCHAR(500) NOT NULL COMMENT '模型路径（官方HuggingFace路径或本地路径）',
    `tokenizer_path` VARCHAR(500) NOT NULL COMMENT 'Tokenizer路径（官方HuggingFace路径或本地路径）',
    `mlm_model_path` VARCHAR(500) COMMENT 'MLM模型路径（用于生成替代词，官方路径或本地路径）',
    `checkpoint_path` VARCHAR(500) COMMENT '微调权重路径（本地路径，可选）',
    `model_source` VARCHAR(50) DEFAULT 'official' COMMENT '模型来源: official(官方)/user(用户上传)',
    `max_length` INT DEFAULT 512 COMMENT '最大长度',
    `status` VARCHAR(50) DEFAULT 'available' COMMENT '状态: available/unavailable',
    `supported_tasks` JSON COMMENT '支持的任务',
    `is_predefined` BOOLEAN DEFAULT FALSE COMMENT '是否预定义',
    `user_id` INT COMMENT '上传/创建用户ID',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    INDEX `idx_model_name` (`model_name`),
    INDEX `idx_model_type` (`model_type`),
    INDEX `idx_model_source` (`model_source`),
    INDEX `idx_status` (`status`),
    INDEX `idx_is_predefined` (`is_predefined`),
    INDEX `idx_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='模型表';

-- ===========================================
-- 数据集表 (datasets)
-- ===========================================
CREATE TABLE IF NOT EXISTS `datasets` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '数据集ID（自增）',
    `dataset_name` VARCHAR(200) NOT NULL COMMENT '数据集名称（唯一）',
    `task_type` VARCHAR(100) NOT NULL COMMENT '任务类型（clone-detection, vulnerability-prediction, code-summarization）',
    `description` TEXT COMMENT '数据集描述',
    `dataset_path` VARCHAR(500) NOT NULL COMMENT '数据集存储路径（目录路径）',
    `file_count` INT DEFAULT 0 COMMENT '文件数量',
    `file_types` JSON COMMENT '文件类型列表（JSON数组，如 ["jsonl", "txt"]）',
    `total_size` BIGINT DEFAULT 0 COMMENT '总大小（字节）',
    `source` VARCHAR(50) DEFAULT 'user' COMMENT '数据集来源: official(官方)/user(用户上传)',
    `status` VARCHAR(50) DEFAULT 'available' COMMENT '状态: available/unavailable',
    `is_predefined` BOOLEAN DEFAULT FALSE COMMENT '是否预定义',
    `user_id` INT COMMENT '上传/创建用户ID',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    UNIQUE KEY `unique_dataset_name` (`dataset_name`),
    INDEX `idx_task_type` (`task_type`),
    INDEX `idx_source` (`source`),
    INDEX `idx_status` (`status`),
    INDEX `idx_is_predefined` (`is_predefined`),
    INDEX `idx_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据集表';

-- ===========================================
-- 任务表 (tasks)
-- ===========================================
CREATE TABLE IF NOT EXISTS `tasks` (
    `id` VARCHAR(100) PRIMARY KEY COMMENT '任务ID（UUID）',
    `task_type` VARCHAR(100) NOT NULL COMMENT '任务类型: attack/single_attack/batch_attack/generate_report/finetune/evaluate_model',
    `sub_task_type` VARCHAR(100) COMMENT '子任务类型（如攻击方法: itgen, beam, alert, mhm, wir, rnns, bayes, style）',

    -- 关联信息
    `model_id` INT COMMENT '使用的模型ID',
    `model_name` VARCHAR(200) COMMENT '模型名称',
    `dataset_name` VARCHAR(200) COMMENT '数据集名称',

    -- 任务状态和进度
    `status` VARCHAR(50) DEFAULT 'pending' COMMENT '任务状态: pending/queued/running/completed/failed/cancelled',
    `priority` INT DEFAULT 5 COMMENT '优先级（1-10，10最高）',
    `progress` FLOAT DEFAULT 0.0 COMMENT '进度(0-100)',
    `progress_message` VARCHAR(500) COMMENT '进度消息',

    -- 任务参数和输入
    `parameters` JSON COMMENT '任务参数（JSON格式）',
    `input_data` JSON COMMENT '输入数据（代码、数据集等）',

    -- 任务结果
    `result` JSON COMMENT '任务结果（JSON格式）',
    `output_files` JSON COMMENT '输出文件路径列表',
    `metrics` JSON COMMENT '评估指标',
    `statistics` JSON COMMENT '统计信息',

    -- 错误处理
    `error_message` TEXT COMMENT '错误信息',
    `error_code` VARCHAR(100) COMMENT '错误代码',

    -- 资源使用
    `resource_usage` JSON COMMENT '资源使用情况（CPU、内存、GPU等）',
    `execution_time` FLOAT COMMENT '执行时间（秒）',

    -- 时间戳
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `queued_at` DATETIME COMMENT '进入队列时间',
    `started_at` DATETIME COMMENT '开始执行时间',
    `completed_at` DATETIME COMMENT '完成时间',

    -- 队列管理
    `queue_name` VARCHAR(100) DEFAULT 'default' COMMENT '队列名称',
    `worker_id` VARCHAR(100) COMMENT '执行任务的worker ID',
    `retry_count` INT DEFAULT 0 COMMENT '重试次数',
    `max_retries` INT DEFAULT 3 COMMENT '最大重试次数',

    -- 用户关联
    `user_id` INT COMMENT '创建任务的用户ID',

    -- 兼容性字段（保留旧字段名）
    `message` VARCHAR(500) COMMENT '状态消息（兼容性字段）',

    -- 向后兼容字段（微调任务）
    `dataset` VARCHAR(200) COMMENT '数据集名称（兼容性字段）',
    `attack_method` VARCHAR(100) COMMENT '攻击方法（兼容性字段）',
    `training_samples` INT COMMENT '训练样本数（兼容性字段）',
    `old_metrics` JSON COMMENT '微调前的指标（兼容性字段）',
    `new_metrics` JSON COMMENT '微调后的指标（兼容性字段）',
    `comparison` JSON COMMENT '指标对比（兼容性字段）',

    -- 批量测试任务专用字段
    `result_file` VARCHAR(500) COMMENT '结果文件路径（兼容性字段）',

    FOREIGN KEY (`model_id`) REFERENCES `models` (`id`) ON DELETE SET NULL,
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    INDEX `idx_task_type` (`task_type`),
    INDEX `idx_sub_task_type` (`sub_task_type`),
    INDEX `idx_status` (`status`),
    INDEX `idx_priority` (`priority`),
    INDEX `idx_model_id` (`model_id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_queue_name` (`queue_name`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务表';

-- ===========================================
-- 评估报告表 (evaluation_reports)
-- ===========================================
CREATE TABLE IF NOT EXISTS `evaluation_reports` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '报告ID（自增）',
    `report_id` VARCHAR(200) NOT NULL UNIQUE COMMENT '报告ID（唯一标识）',
    `model_name` VARCHAR(200) NOT NULL COMMENT '模型名称',
    `task_type` VARCHAR(100) NOT NULL COMMENT '任务类型',
    `attack_methods` JSON COMMENT '攻击方法列表',
    `evaluation_metrics` JSON COMMENT '评估指标列表',

    -- 总体指标
    `total_samples` INT DEFAULT 0 COMMENT '总样本数',
    `successful_attacks` INT DEFAULT 0 COMMENT '成功攻击数',
    `failed_attacks` INT DEFAULT 0 COMMENT '失败攻击数',

    -- ASR - Attack Success Rate (攻击成功率)
    `asr` FLOAT DEFAULT 0.0 COMMENT '攻击成功率',
    -- AMI - Average Model Invocations (平均模型调用次数)
    `ami` FLOAT DEFAULT 0.0 COMMENT '平均模型调用次数',
    -- ART - Average Response Time (平均响应时间)
    `art` FLOAT DEFAULT 0.0 COMMENT '平均响应时间（分钟）',

    -- 额外统计
    `avg_program_length` FLOAT DEFAULT 0.0 COMMENT '平均程序长度',
    `avg_identifiers` FLOAT DEFAULT 0.0 COMMENT '平均标识符数量',

    -- 详细结果
    `method_metrics` JSON COMMENT '各攻击方法的详细指标',
    `summary_stats` JSON COMMENT '汇总统计',
    `sample_results` JSON COMMENT '样本结果',

    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX `idx_report_id` (`report_id`),
    INDEX `idx_model_name` (`model_name`),
    INDEX `idx_task_type` (`task_type`),
    INDEX `idx_asr` (`asr`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='评估报告表';

-- ===========================================
-- 插入初始数据
-- ===========================================

-- 插入管理员用户
INSERT INTO `users` (`username`, `email`, `password_hash`, `full_name`, `role`, `status`, `email_verified`)
VALUES ('admin', 'admin@itgen.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeCt0Nxj1fXGXaXa', '系统管理员', 'admin', 'active', TRUE)
ON DUPLICATE KEY UPDATE `updated_at` = CURRENT_TIMESTAMP;

-- 插入预定义模型数据
INSERT INTO `models` (`model_name`, `model_type`, `description`, `model_path`, `tokenizer_path`, `mlm_model_path`, `model_source`, `max_length`, `supported_tasks`, `is_predefined`, `user_id`)
VALUES
('codebert-base', 'CodeBERT', '微软CodeBERT基础模型，支持代码理解和生成任务', 'microsoft/codebert-base', 'microsoft/codebert-base', 'microsoft/codebert-base-mlm', 'official', 512, '["clone-detection", "vulnerability-prediction", "code-summarization"]', TRUE, 1),
('graphcodebert-base', 'GraphCodeBERT', '微软GraphCodeBERT基础模型，增强的代码理解能力', 'microsoft/graphcodebert-base', 'microsoft/graphcodebert-base', 'microsoft/graphcodebert-base', 'official', 512, '["clone-detection", "vulnerability-prediction"]', TRUE, 1),
('codet5-base', 'CodeT5', 'Salesforce CodeT5基础模型，支持多种代码任务', 'Salesforce/codet5-base', 'Salesforce/codet5-base', NULL, 'official', 512, '["clone-detection", "code-summarization"]', TRUE, 1),
('unixcoder-base', 'UniXcoder', '微软UniXcoder统一代码模型', 'microsoft/unixcoder-base', 'microsoft/unixcoder-base', NULL, 'official', 512, '["clone-detection", "vulnerability-prediction", "code-summarization"]', TRUE, 1)
ON DUPLICATE KEY UPDATE `updated_at` = CURRENT_TIMESTAMP;

-- 插入预定义数据集
INSERT INTO `datasets` (`dataset_name`, `task_type`, `description`, `dataset_path`, `file_count`, `file_types`, `source`, `status`, `is_predefined`, `user_id`)
VALUES
('clone-detection-test', 'clone-detection', '代码克隆检测测试数据集', '/datasets/clone-detection/test', 100, '["jsonl"]', 'official', 'available', TRUE, 1),
('vulnerability-test', 'vulnerability-prediction', '漏洞检测测试数据集', '/datasets/vulnerability/test', 200, '["jsonl"]', 'official', 'available', TRUE, 1),
('code-summarization-test', 'code-summarization', '代码摘要生成测试数据集', '/datasets/code-summarization/test', 150, '["jsonl"]', 'official', 'available', TRUE, 1)
ON DUPLICATE KEY UPDATE `updated_at` = CURRENT_TIMESTAMP;

-- ===========================================
-- 创建索引和约束（可选优化）
-- ===========================================

-- 为常用查询创建复合索引
CREATE INDEX IF NOT EXISTS `idx_tasks_status_priority` ON `tasks` (`status`, `priority`);
CREATE INDEX IF NOT EXISTS `idx_tasks_user_created` ON `tasks` (`user_id`, `created_at`);
CREATE INDEX IF NOT EXISTS `idx_evaluation_model_task` ON `evaluation_reports` (`model_name`, `task_type`);

-- ===========================================
-- 完成提示
-- ===========================================

SELECT 'ITGen database created successfully!' AS status;
SELECT
    (SELECT COUNT(*) FROM users) AS users_count,
    (SELECT COUNT(*) FROM models) AS models_count,
    (SELECT COUNT(*) FROM datasets) AS datasets_count,
    (SELECT COUNT(*) FROM tasks) AS tasks_count,
    (SELECT COUNT(*) FROM evaluation_reports) AS reports_count;
