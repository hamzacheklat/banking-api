from sqlalchemy import create_engine, text

engine = create_engine("oracle+cx_oracle://user:password@host:1521/?service_name=MONSERVICE")

ddl = """
CREATE TABLE product_action_available (
    product_name VARCHAR2(255) NOT NULL,
    action_name  VARCHAR2(100) NOT NULL,
    status       VARCHAR2(10) NOT NULL,
    updated_by   VARCHAR2(100),
    updated_at   TIMESTAMP DEFAULT SYSDATE,
    CONSTRAINT pk_product_action PRIMARY KEY (product_name, action_name)
)
"""

with engine.connect() as conn:
    try:
        conn.execute(text(ddl))
        conn.commit()
        print("✅ Table product_action_available créée avec succès !")
    except Exception as e:
        print("⚠️ Erreur :", e)
