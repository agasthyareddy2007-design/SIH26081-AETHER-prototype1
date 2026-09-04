from pathlib import Path
from src.engine.forecasting_engine import ForecastingEngine
from src.engine.aether_assistant import AETHERAssistant

def main():
    print("Loading PyTorch MLP Engine & Qwen2.5-3B-Instruct on RTX 5080...")
    
    engine = ForecastingEngine(
        config_path=Path("config/data_config.yaml"),
        model_path=Path("models/blender/mlp_gating_model")
    )
    assistant = AETHERAssistant(engine=engine)

    print("=" * 50)
    print("AETHER Weather Intelligence Assistant")
    print("Type your questions below. Type 'exit' to quit.")
    print("=" * 50)

    while True:
        try:
            query = input("You > ").strip()
            if not query:
                continue
            if query.lower() in ["exit", "quit", "q"]:
                print("Exiting AETHER.")
                break

            response = assistant.chat(query)
            print(f"\nAETHER > {response}\n")
        except (KeyboardInterrupt, EOFError):
            print("\nSession terminated.")
            break

if __name__ == "__main__":
    main()