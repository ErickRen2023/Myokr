-- issue#7: 为 KR 添加 sort_order 列，支持拖拽排序

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
