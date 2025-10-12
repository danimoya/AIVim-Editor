#!/usr/bin/env python3
"""
Helper script to download a small local LLM model for AIVim.
This script will download a model from Hugging Face to use with the local LLM feature.
"""
import os
import sys
import argparse
import logging
import requests
from tqdm import tqdm

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Default model options
DEFAULT_MODELS = {
    "tinyllama": {
        "name": "TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf",
        "url": "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
        "size_mb": 642,
        "description": "TinyLlama 1.1B - Very small and fast model (~642MB)"
    },
    "phi2": {
        "name": "phi-2.Q4_K_M.gguf",
        "url": "https://huggingface.co/TheBloke/phi-2-GGUF/resolve/main/phi-2.Q4_K_M.gguf",
        "size_mb": 1600,
        "description": "Microsoft Phi-2 - Good quality small model (~1.6GB)"
    },
    "stablelm": {
        "name": "stablelm-zephyr-3b.Q4_K_M.gguf",
        "url": "https://huggingface.co/TheBloke/StableLM-Zephyr-3B-GGUF/resolve/main/stablelm-zephyr-3b.Q4_K_M.gguf",
        "size_mb": 1900,
        "description": "StableLM Zephyr 3B - Balanced quality small model (~1.9GB)"
    }
}

def download_file(url, destination, model_name=None):
    """
    Download a file with progress bar
    
    Args:
        url: URL to download
        destination: Destination path
        model_name: Optional model name for display
    """
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Get file size
        total_size = int(response.headers.get('content-length', 0))
        
        # Create the download directory if it doesn't exist
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        # Display model name in progress message if provided
        desc = f"Downloading {model_name}" if model_name else "Downloading"
        
        # Download with progress bar
        with open(destination, 'wb') as f, tqdm(
                desc=desc,
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
            ) as bar:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:  # filter out keep-alive chunks
                    f.write(chunk)
                    bar.update(len(chunk))
        
        logger.info(f"Download complete: {destination}")
        return True
    except Exception as e:
        logger.error(f"Download failed: {str(e)}")
        return False

def list_models():
    """List available models with description"""
    print("\nAvailable models for download:")
    print("-" * 70)
    for key, model in DEFAULT_MODELS.items():
        print(f"{key}: {model['description']}")
    print("-" * 70)
    print("Usage example: python download_local_model.py --model tinyllama")
    print("\nYou can also download a model by providing a direct URL:")
    print("python download_local_model.py --url https://example.com/model.gguf --output models/custom_model.gguf")
    print("-" * 70)

def main():
    """Main function to download a model"""
    parser = argparse.ArgumentParser(description="Download a local LLM model for AIVim")
    
    # Create a mutually exclusive group for model sources
    model_source = parser.add_mutually_exclusive_group(required=False)
    model_source.add_argument("--model", choices=DEFAULT_MODELS.keys(), 
                             help="Name of the predefined model to download")
    model_source.add_argument("--url", help="Direct URL to download a GGUF model file")
    
    # Output path option
    parser.add_argument("--output", help="Custom output path for the downloaded model")
    
    # List models option
    parser.add_argument("--list", action="store_true", help="List available predefined models")
    
    args = parser.parse_args()
    
    # List models and exit if requested
    if args.list or (not args.model and not args.url):
        list_models()
        return
    
    # Download a predefined model
    if args.model:
        model_info = DEFAULT_MODELS[args.model]
        model_name = model_info["name"]
        model_url = model_info["url"]
        
        # Set output path
        if args.output:
            output_path = args.output
        else:
            output_path = os.path.join("models", model_name)
            
        logger.info(f"Downloading {args.model} model ({model_info['size_mb']} MB)...")
        success = download_file(model_url, output_path, model_name)
        
        if success:
            # Set environment variable for the downloaded model
            os.environ["LLAMA_MODEL_PATH"] = output_path
            
            logger.info(f"\nModel downloaded successfully to: {output_path}")
            logger.info("To use this model with AIVim, set the environment variable:")
            logger.info(f"export LLAMA_MODEL_PATH={os.path.abspath(output_path)}")
            
            # Create a .env file with model path
            with open('.env', 'a') as env_file:
                env_file.write(f"\n# Local LLM model path\nLLAMA_MODEL_PATH={os.path.abspath(output_path)}\n")
            logger.info("Added model path to .env file")
    
    # Download from custom URL
    elif args.url:
        if not args.output:
            # Extract filename from URL if no output path specified
            filename = os.path.basename(args.url)
            output_path = os.path.join("models", filename)
        else:
            output_path = args.output
            
        logger.info(f"Downloading model from custom URL...")
        success = download_file(args.url, output_path)
        
        if success:
            # Set environment variable for the downloaded model
            os.environ["LLAMA_MODEL_PATH"] = output_path
            
            logger.info(f"\nModel downloaded successfully to: {output_path}")
            logger.info("To use this model with AIVim, set the environment variable:")
            logger.info(f"export LLAMA_MODEL_PATH={os.path.abspath(output_path)}")
            
            # Create a .env file with model path
            with open('.env', 'a') as env_file:
                env_file.write(f"\n# Local LLM model path\nLLAMA_MODEL_PATH={os.path.abspath(output_path)}\n")
            logger.info("Added model path to .env file")
    
    # Run the test script
    if 'success' in locals() and success:
        logger.info("\nTesting local LLM integration...")
        import subprocess
        result = subprocess.run(
            ["python", "tests/test_local_llm.py"],
            check=False,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logger.error(f"Test failed: {result.stderr}")
        else:
            logger.info("Test passed successfully")

if __name__ == "__main__":
    main()