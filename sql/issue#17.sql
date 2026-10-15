ALTER TABLE progress_record ADD COLUMN target_snapshot JSON NULL COMMENT '记录时的目标配置；旧记录为空';
