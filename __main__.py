import sys
import zipfile
import logging
from pathlib import Path
from omegaconf import OmegaConf, DictConfig
from hydra import compose, initialize
from hydra.core.global_hydra import GlobalHydra
from hydra.core.config_store import ConfigStore
from hydra.plugins.search_path_plugin import SearchPathPlugin
from hydra.core.config_search_path import ConfigSearchPath

class ZipConfigPlugin(SearchPathPlugin):
    """Плагин Hydra 1.3+ для загрузки конфигов из zip-архива"""
    def __init__(self, zip_path: str):
        self.zip_path = zip_path
        self.zip_file = zipfile.ZipFile(zip_path)
        self._configs = {}
        self._load_configs()
    
    def _load_configs(self):
        """Загружает все YAML-конфиги из архива в память"""
        for name in self.zip_file.namelist():
            if name.startswith('configs/') and (name.endswith('.yaml') or name.endswith('.yml')):
                with self.zip_file.open(name) as f:
                    content = f.read().decode('utf-8')
                    self._configs[name] = OmegaConf.create(content)
    
    def manipulate_search_path(self, search_path: ConfigSearchPath) -> None:
        """Добавляем виртуальный источник конфигов"""
        # Основной путь к конфигурации
        search_path.append(provider="zip-config", path="memory://configs")
        
        # Пути Hydra
        search_path.append("hydra", "pkg://hydra.conf")
        search_path.append("hydra", "pkg://hydra_plugins")

    def get_config(self, config_path: str) -> OmegaConf:
        """Возвращает конфиг по его пути в виртуальной файловой системе"""
        # Нормализуем путь
        path = Path(config_path)
        if not path.suffix:
            path = path.with_suffix(".yaml")
        
        # Ищем точное совпадение
        if str(path) in self._configs:
            return self._configs[str(path)]
        
        # Ищем в поддиректориях
        for full_path, conf in self._configs.items():
            if full_path.endswith(str(path)):
                return conf
        
        # Конфиг не найден
        raise FileNotFoundError(f"Config not found: {config_path}")

def register_zip_plugin(zip_path: str):
    """Регистрирует плагин для работы с zip-архивом"""
    # Очищаем предыдущее состояние Hydra
    GlobalHydra.instance().clear()
    
    # Создаем и регистрируем плагин
    plugin = ZipConfigPlugin(zip_path)
    
    # Создаем search path
    search_path = ConfigSearchPath()
    plugin.manipulate_search_path(search_path)
    
    # Инициализируем Hydra с кастомным search path
    GlobalHydra.instance().initialize(
        config_search_path=search_path,
        job_name="zip_app",
        strict=False
    )
    
    # Возвращаем плагин для доступа к конфигам
    return plugin

def main(zip_path: str, overrides: list) -> DictConfig:
    """Основная функция инициализации Hydra"""
    # Регистрируем плагин и получаем доступ к конфигам
    plugin = register_zip_plugin(zip_path)
    
    # Композиция конфигурации
    return compose(
        config_name="config", 
        overrides=overrides,
        return_hydra_config=True
    )

def load_app_module(zip_path: str):
    """Загружает основной модуль приложения из архива"""
    # Временная добавка пути для импорта
    if zip_path not in sys.path:
        sys.path.insert(0, zip_path)
    
    # Динамический импорт
    import src.train
    return src.train

if __name__ == "__main__":
    # Настройка логов для отладки
    logging.basicConfig(level=logging.INFO)
    
    # Путь к архиву - первый аргумент
    zip_path = sys.argv[0]
    
    # Аргументы переопределения конфига
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