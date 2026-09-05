-- =========================================================
-- RevenueOS - PostgreSQL Database Schema
-- =========================================================

-- =========================================================
-- 1. CUSTOMERS
-- =========================================================

CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(100) PRIMARY KEY,

    customer_age_days INTEGER DEFAULT 0,

    previous_successful_payments INTEGER DEFAULT 0,

    previous_failed_payments INTEGER DEFAULT 0,

    customer_success_rate NUMERIC(6,4),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- =========================================================
-- 2. PAYMENTS
-- =========================================================

CREATE TABLE IF NOT EXISTS payments (
    transaction_id VARCHAR(100) PRIMARY KEY,

    customer_id VARCHAR(100) NOT NULL,

    payment_method VARCHAR(50),

    amount NUMERIC(12,2) NOT NULL,

    status VARCHAR(20) NOT NULL,

    failure_reason VARCHAR(100),

    failure_category VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_payment_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
        ON DELETE CASCADE
);


-- =========================================================
-- 3. RECOVERY OPPORTUNITIES
-- =========================================================

CREATE TABLE IF NOT EXISTS recovery_opportunities (
    id SERIAL PRIMARY KEY,

    transaction_id VARCHAR(100) UNIQUE NOT NULL,

    customer_id VARCHAR(100),

    amount NUMERIC(12,2),

    recovery_probability NUMERIC(6,4),

    expected_recovery_value NUMERIC(12,2),

    priority VARCHAR(20),

    recommended_action VARCHAR(255),

    failure_category VARCHAR(100),

    failure_reason VARCHAR(100),

    payment_method VARCHAR(50),

    recovery_status VARCHAR(30) DEFAULT 'PENDING',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_recovery_transaction
        FOREIGN KEY (transaction_id)
        REFERENCES payments(transaction_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_recovery_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
        ON DELETE SET NULL
);


-- =========================================================
-- 4. RECOVERY EXECUTIONS
-- =========================================================

CREATE TABLE IF NOT EXISTS recovery_executions (
    id SERIAL PRIMARY KEY,

    transaction_id VARCHAR(100) NOT NULL,

    action VARCHAR(255),

    result VARCHAR(100),

    message TEXT,

    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_execution_transaction
        FOREIGN KEY (transaction_id)
        REFERENCES payments(transaction_id)
        ON DELETE CASCADE
);


-- =========================================================
-- 5. INDEXES
-- =========================================================

CREATE INDEX IF NOT EXISTS idx_payments_status
ON payments(status);

CREATE INDEX IF NOT EXISTS idx_payments_customer
ON payments(customer_id);

CREATE INDEX IF NOT EXISTS idx_recovery_priority
ON recovery_opportunities(priority);

CREATE INDEX IF NOT EXISTS idx_recovery_status
ON recovery_opportunities(recovery_status);

CREATE INDEX IF NOT EXISTS idx_recovery_customer
ON recovery_opportunities(customer_id);

CREATE INDEX IF NOT EXISTS idx_execution_transaction
ON recovery_executions(transaction_id);


-- =========================================================
-- 6. VERIFY TABLES
-- =========================================================

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(50) DEFAULT 'ADMIN',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email
ON users(email);