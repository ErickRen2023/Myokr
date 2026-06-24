-- MyOKR V0.2 数据库初始化脚本
-- 适用：MySQL 8.0+
-- 用法：mysql -u root -p < init.sql
-- 注意：无外键约束，引用完整性由业务层保障

CREATE DATABASE IF NOT EXISTS myokr
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE myokr;

-- ============================================================
-- 1. user — 用户表
-- ============================================================
CREATE TABLE user (
    id          BIGINT       NOT NULL AUTO_INCREMENT  PRIMARY KEY,
    key_hash    VARCHAR(255) NOT NULL                 COMMENT 'bcrypt(cost=12) 哈希后的秘钥',
    key_prefix  VARCHAR(32)  NOT NULL DEFAULT ''      COMMENT 'SHA256(raw_key)[:16] 用于索引加速登录',
    create_time DATETIME     NOT NULL DEFAULT NOW()   COMMENT '身份创建时间',
    update_time DATETIME     NOT NULL DEFAULT NOW() ON UPDATE NOW()
                                                      COMMENT '秘钥最后重置时间',

    INDEX idx_user_key_prefix (key_prefix)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 2. cycle — 时间周期表
-- ============================================================
CREATE TABLE cycle (
    id          BIGINT       NOT NULL AUTO_INCREMENT  PRIMARY KEY,
    user_id     BIGINT       NOT NULL                 COMMENT '归属用户',
    name        VARCHAR(100) NOT NULL                 COMMENT '周期名称',
    type        TINYINT      NOT NULL                 COMMENT '1=monthly 2=bimonthly 3=quarterly 4=half_year 5=yearly',
    start_date  DATE         NOT NULL                 COMMENT '周期开始日期',
    end_date    DATE         NOT NULL                 COMMENT '周期结束日期',
    status      TINYINT      NOT NULL DEFAULT 0       COMMENT '0=active 1=completed',
    create_time DATETIME     NOT NULL DEFAULT NOW(),
    update_time DATETIME     NOT NULL DEFAULT NOW() ON UPDATE NOW(),

    INDEX idx_cycle_user_status (user_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 3. objective — 目标表 (O)
-- ============================================================
CREATE TABLE objective (
    id          BIGINT       NOT NULL AUTO_INCREMENT  PRIMARY KEY,
    user_id     BIGINT       NOT NULL                 COMMENT '归属用户 (冗余列，加速归属校验)',
    cycle_id    BIGINT       NOT NULL                 COMMENT '所属周期',
    title       VARCHAR(500) NOT NULL                 COMMENT '目标标题',
    description TEXT         NULL                     COMMENT '目标背景与细节描述',
    sort_order  INT          NOT NULL DEFAULT 0       COMMENT '排序优先级，越小越靠前',
    status      TINYINT      NOT NULL DEFAULT 0       COMMENT '0=active 1=archived',
    create_time DATETIME     NOT NULL DEFAULT NOW(),
    update_time DATETIME     NOT NULL DEFAULT NOW() ON UPDATE NOW(),

    INDEX idx_obj_user_cycle (user_id, cycle_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 4. key_result — 关键结果表 (KR)
-- ============================================================
CREATE TABLE key_result (
    id            BIGINT        NOT NULL AUTO_INCREMENT  PRIMARY KEY,
    objective_id  BIGINT        NOT NULL                 COMMENT '归属目标',
    title         VARCHAR(500)  NOT NULL                 COMMENT 'KR 标题',
    description   TEXT          NULL                     COMMENT 'KR 详细描述',
    type          TINYINT       NOT NULL                 COMMENT '1=numeric 2=milestone 3=boolean',
    target        JSON          NOT NULL                 COMMENT '目标配置',
    current_value DOUBLE        NULL                     COMMENT '当前进度值 (numeric 型)',
    is_achieved   TINYINT(1)    NOT NULL DEFAULT 0       COMMENT '0=未达成 1=已达成',
    status        TINYINT       NOT NULL DEFAULT 0       COMMENT '0=active 1=archived',
    create_time   DATETIME      NOT NULL DEFAULT NOW(),
    update_time   DATETIME      NOT NULL DEFAULT NOW() ON UPDATE NOW(),

    INDEX idx_kr_objective (objective_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 5. milestone — 里程碑节点表
-- ============================================================
CREATE TABLE milestone (
    id            BIGINT       NOT NULL AUTO_INCREMENT  PRIMARY KEY,
    key_result_id BIGINT       NOT NULL                 COMMENT '归属 KR',
    description   VARCHAR(500) NOT NULL                 COMMENT '里程碑描述',
    completed     TINYINT(1)   NOT NULL DEFAULT 0       COMMENT '0=未完成 1=已完成',
    sort_order    INT          NOT NULL DEFAULT 0       COMMENT '排序序号',
    is_deleted    TINYINT      NOT NULL DEFAULT 0       COMMENT '0=未删除 1=已删除（软删除）',
    create_time   DATETIME     NOT NULL DEFAULT NOW(),
    update_time   DATETIME     NOT NULL DEFAULT NOW() ON UPDATE NOW(),

    INDEX idx_ms_kr (key_result_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 6. progress_record — 进度记录表 (不可变，只追加)
-- ============================================================
CREATE TABLE progress_record (
    id            BIGINT         NOT NULL AUTO_INCREMENT  PRIMARY KEY,
    key_result_id BIGINT         NOT NULL                 COMMENT '归属 KR',
    value         DECIMAL(10,2)  NOT NULL                 COMMENT '该次更新的进度值',
    is_achieved   TINYINT(1)     NOT NULL DEFAULT 0       COMMENT '该次更新是否代表达成目标',
    recorded_at   DATETIME       NOT NULL DEFAULT NOW()   COMMENT '记录时间',

    INDEX idx_pr_kr_time (key_result_id, recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
