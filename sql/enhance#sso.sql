-- MyOKR enhance#sso
-- Dialect: MySQL 8.4
-- 将原秘钥身份模型切换为 aSSO-only；user.id 直接保存 aSSO user_id。
-- 本脚本只执行一次，不使用 migrate。

USE myokr;

ALTER TABLE `user`
    DROP COLUMN `key_hash`,
    DROP COLUMN `key_prefix`,
    MODIFY COLUMN `id` BIGINT NOT NULL COMMENT 'aSSO user_id';
