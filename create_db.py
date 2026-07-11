import sys
import psycopg

def create_database(db_name: str):
    # Base URL pointing to defaultdb
    conn_str = "postgresql://dinakar:Td_o1DuoEuPWLsUAZwtHRw@hip-snapper-29039.j77.aws-ap-south-1.cockroachlabs.cloud:26257/defaultdb?sslmode=verify-full"
    
    print(f"Connecting to CockroachDB to create database '{db_name}'...")
    try:
        # Connect to defaultdb with autocommit=True (needed for CREATE DATABASE)
        with psycopg.connect(conn_str, autocommit=True) as conn:
            with conn.cursor() as cur:
                # Check if database already exists
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
                exists = cur.fetchone()
                
                if exists:
                    print(f"Database '{db_name}' already exists.")
                else:
                    cur.execute(f"CREATE DATABASE {db_name}")
                    print(f"Database '{db_name}' created successfully!")
                    
    except Exception as e:
        print("Failed to create database:", e)

if __name__ == "__main__":
    name = "careerhive"
    if len(sys.argv) > 1:
        name = sys.argv[1]
    create_database(name)
