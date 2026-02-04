TRUNCATE TABLE finance_user CASCADE;
"BEGIN;
-- Désactive les vérifications de clés étrangères
SET CONSTRAINTS ALL DEFERRED; 
-- Ou de manière plus radicale
ALTER TABLE finance_user_groups DISABLE TRIGGER ALL;
ALTER TABLE finance_otp DISABLE TRIGGER ALL;

TRUNCATE TABLE finance_user;

-- Réactive les vérifications
ALTER TABLE finance_user_groups ENABLE TRIGGER ALL;
ALTER TABLE finance_otp ENABLE TRIGGER ALL;
COMMIT;"