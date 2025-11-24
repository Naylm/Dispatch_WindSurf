-- Ajouter la colonne force_password_reset pour forcer la réinitialisation
-- Cette colonne permet aux admins de forcer un utilisateur à réinitialiser son mot de passe

-- Table users - PostgreSQL compatible
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='users' AND column_name='force_password_reset') THEN
        ALTER TABLE users ADD COLUMN force_password_reset INTEGER DEFAULT 0;
    END IF;
END $$;

-- Table techniciens - PostgreSQL compatible
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='techniciens' AND column_name='force_password_reset') THEN
        ALTER TABLE techniciens ADD COLUMN force_password_reset INTEGER DEFAULT 0;
    END IF;
END $$;

-- Mettre à jour tous les utilisateurs avec des mots de passe non hashés
-- pour forcer la réinitialisation
UPDATE users
SET force_password_reset = 1
WHERE password IS NULL
   OR password = ''
   OR (password NOT LIKE 'pbkdf2:%' AND password NOT LIKE 'scrypt:%');

UPDATE techniciens
SET force_password_reset = 1
WHERE password IS NULL
   OR password = ''
   OR (password NOT LIKE 'pbkdf2:%' AND password NOT LIKE 'scrypt:%');
