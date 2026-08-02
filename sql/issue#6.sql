-- issue#6: 为 KR 添加详细描述字段
-- 将原有 description 的内容迁移到新 title 列，再将 description 改为 TEXT 类型用于详细描述
-- 适用于已有数据库的迁移

-- Step 1: 新增 title 列
ALTER TABLE key_result ADD COLUMN title VARCHAR(500) NOT NULL DEFAULT '' COMMENT 'KR 标题' AFTER objective_id;

-- Step 2: 将原有 description 数据迁移到 title
UPDATE key_result SET title = description;

-- Step 3: 移除 title 的默认值（数据已回填完毕，不再需要）
ALTER TABLE key_result ALTER COLUMN title DROP DEFAULT;

-- Step 4: 将原 description 列改为详细描述字段（清空旧数据，原有内容已迁移到 title）
ALTER TABLE key_result MODIFY COLUMN description TEXT NULL COMMENT 'KR 详细描述';
UPDATE key_result SET description = NULL;
