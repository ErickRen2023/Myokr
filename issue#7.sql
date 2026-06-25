-- issue#7: 为 KR 添加 sort_order 列，支持拖拽排序
-- 适用于已有数据库的迁移
--
-- 执行方式（本机）：
--   scp server/issue#7.sql root@<VPS_IP>:/tmp/issue#7.sql
--   ssh root@<VPS_IP>
--   docker exec -i myokr-mysql mysql -u root -p myokr < /tmp/issue#7.sql
--
-- 验证：
--   docker exec -i myokr-mysql mysql -u root -p myokr -e "SHOW COLUMNS FROM key_result LIKE 'sort_order';"

ALTER TABLE key_result
  ADD COLUMN sort_order INT NOT NULL DEFAULT 0
  COMMENT '排序优先级，越小越靠前' AFTER is_achieved;

-- Backfill: 按 objective_id 分组，按 id 升序为已有活跃 KR 分配连续 sort_order
UPDATE key_result kr
INNER JOIN (
    SELECT id,
           ROW_NUMBER() OVER (PARTITION BY objective_id ORDER BY id) - 1 AS rn
    FROM key_result
    WHERE status = 0
) ranked ON kr.id = ranked.id
SET kr.sort_order = ranked.rn;
