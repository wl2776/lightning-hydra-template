import sys
import zipfile
import logging
from pathlib import Path
from omegaconf import OmegaConf, DictConfig
from hydra import compose, initialize
from hydra.core.global_hydra import GlobalHydra
from hydra.core.config_store import ConfigStore

class ZipConfigLoader:
    """Загрузчик конфигураций из zip-архива"""
    def __init__(self, zip_path: str):
        self.zip_path = zip_path
        self.zip_file = zipfile.ZipFile(zip_path)
        self.configs = {}
        self.load_all_configs()
    
    def load_all_configs(self):
        """Загружает все YAML-конфиги из архива в память"""
        for name in self.zip_file.namelist():
            if self.is_valid_config(name):
                with self.zip_file.open(name) as f:
                    content = f.read().decode('utf-8')
                    key = self.get_config_key(name)
                    self.configs[key] = OmegaConf.create(content)
    
    def is_valid_config(self, name: str) -> bool:
        """Проверяет, является ли файл валидным конфигом"""
        return (
            name.startswith('configs/') and 
            (name.endswith('.yaml') or name.endswith('.yml')) and
            not name.endswith('/')  # Исключаем директории
        )
    
    def get_config_key(self, path: str) -> str:
        """Преобразует путь к конфигу в ключ для ConfigStore"""
        # Удаляем 'configs/' в начале и расширение файла
        key = path[8:]
        if key.endswith('.yaml'):
            key = key[:-5]
        elif key.endswith('.yml'):
            key = key[:-4]
        return key
    
    def register_configs(self):
        """Регистрирует все конфиги в Hydra ConfigStore"""
        cs = ConfigStore.instance()
        for key, conf in self.configs.items():
            # Разделяем ключ на группу и имя конфига
            parts = key.split('/')
            if len(parts) == 1:
                # Основные конфиги без группы
                cs.store(name=parts[0], node=conf)
            else:
                # Конфиги с группами (dataset, model и т.д.)
                group = '/'.join(parts[:-1])
                name = parts[-1]
                cs.store(name=name, group=group, node=conf)

def initialize_hydra_with_zip_configs(zip_path: str):
    """Инициализирует Hydra с конфигами из zip-архива"""
    # Очищаем предыдущее состояние Hydra
    GlobalHydra.instance().clear()
    
    # Загрузка конфигов из архива
    loader = ZipConfigLoader(zip_path)
    
    # Регистрация конфигов в ConfigStore
    loader.register_configs()
    
    # Инициализация Hydra
    initialize(config_path=None, job_name="zip_app")

def compose_config(overrides: list) -> DictConfig:
    """Создает конфигурацию с переопределениями"""
    return compose(
        config_name="config", 
        overrides=overrides,
        return_hydra_config=False
    )

def load_app_module(zip_path: str):
    """Загружает основной модуль приложения из архива"""
    # Временная добавка пути для импорта
    if zip_path not in sys.path:
        sys.path.insert(0, zip_path)
    
    # Динамический импорт
    import src.train
    return src.train

def main(zip_path: str, overrides: list) -> DictConfig:
    """Основная функция инициализации"""
    # Инициализация Hydra с конфигами из архива
    initialize_hydra_with_zip_configs(zip_path)
    
    # Композиция конфигурации
    return compose_config(overrides)

if __name__ == "__main__":
    # Настройка логов
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s][%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Путь к архиву и переопределения
    zip_path = sys.argv[0]
    overrides = sys.argv[1:]
    
    try:
        # Загрузка конфигурации
        cfg = main(zip_path, overrides)
        
        # Загрузка и запуск приложения
        app = load_app_module(zip_path)
        app.main(cfg)
    
    except Exception as e:
        logging.exception("Application failed")
        sys.exit(1)