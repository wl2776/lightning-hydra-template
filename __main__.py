import hydra
from omegaconf import DictConfig
from src.train import main
from plugins import ZipSearchPathPlugin  # Импортируем наш класс

# Регистрация плагина
cs = hydra.core.global_hydra.GlobalHydras.instance().hydras[0].config_loader.config_store
cs.store(name="zip_config", node=ZipSearchPathPlugin())

@hydra.main(config_path=".", config_name="config")
def main(cfg: DictConfig):
    print("Loaded configuration:")
    print(OmegaConf.to_yaml(cfg))
    
    # Логика обучения
    trainer = Trainer(cfg)
    trainer.train()

