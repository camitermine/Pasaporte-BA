from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    motor_db: str = "mysql"
    actividad_db: str = "hbase"
    mysql_url: str = "mysql+pymysql://pasaporte:pasaporte@localhost:3307/pasaporteba?charset=utf8mb4"
    hbase_host: str = "localhost"
    hbase_port: int = 9090

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

MOTORES = ("mysql", "hbase")
