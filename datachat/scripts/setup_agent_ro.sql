-- 项目三：为 Agent 创建只读账号（在 WSL MySQL 中执行）
-- 用法: mysql -uroot -p123456 < setup_agent_ro.sql
CREATE USER IF NOT EXISTS 'agent_ro'@'%' IDENTIFIED BY '123456';
GRANT SELECT ON mall_ads.* TO 'agent_ro'@'%';
FLUSH PRIVILEGES;
SELECT user, host FROM mysql.user WHERE user = 'agent_ro';
