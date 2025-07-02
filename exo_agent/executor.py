import os
import time
import logging
import json
import torch
import psutil
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM, 
    GenerationConfig,
    pipeline
)
from shared.config.env import (
    DEFAULT_MODEL, 
    MODEL_CACHE_DIR, 
    MAX_MODEL_MEMORY
)

logger = logging.getLogger(__name__)

class ModelInferenceEngine:
    """Advanced model inference engine with caching and optimization."""
    
    def __init__(self):
        self.models = {}  # Cache for loaded models
        self.tokenizers = {}  # Cache for loaded tokenizers
        self.device = self._get_optimal_device()
        self.cache_dir = Path(MODEL_CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Inference engine initialized on device: {self.device}")
    
    def _get_optimal_device(self) -> str:
        """Determine the best device for inference."""
        if torch.cuda.is_available():
            # Check GPU memory
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3  # GB
            logger.info(f"GPU available with {gpu_memory:.1f}GB memory")
            return "cuda:0"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            logger.info("Using Apple MPS backend")
            return "mps"
        else:
            logger.info("Using CPU for inference")
            return "cpu"
    
    def _check_memory_usage(self) -> Dict[str, float]:
        """Check current memory usage."""
        memory_info = {
            "cpu_percent": psutil.virtual_memory().percent,
            "cpu_available_gb": psutil.virtual_memory().available / 1024**3
        }
        
        if torch.cuda.is_available():
            memory_info.update({
                "gpu_allocated_gb": torch.cuda.memory_allocated() / 1024**3,
                "gpu_reserved_gb": torch.cuda.memory_reserved() / 1024**3
            })
        
        return memory_info
    
    def _load_model(self, model_name: str) -> tuple:
        """Load model and tokenizer with caching."""
        if model_name in self.models:
            logger.debug(f"Using cached model: {model_name}")
            return self.models[model_name], self.tokenizers[model_name]
        
        logger.info(f"Loading model: {model_name}")
        start_time = time.time()
        
        try:
            # Check available memory before loading
            memory_info = self._check_memory_usage()
            logger.debug(f"Memory before loading: {memory_info}")
            
            # Load tokenizer
            tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                cache_dir=self.cache_dir,
                trust_remote_code=True
            )
            
            # Add padding token if not present
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            
            # Determine model loading strategy based on available resources
            model_kwargs = {
                "cache_dir": self.cache_dir,
                "trust_remote_code": True,
                "torch_dtype": torch.float16 if self.device != "cpu" else torch.float32
            }
            
            # Load model with appropriate precision
            if self.device == "cpu" or memory_info.get("cpu_available_gb", 0) < 8:
                # Use 8-bit quantization for memory efficiency
                try:
                    model_kwargs["load_in_8bit"] = True
                    logger.info("Loading model with 8-bit quantization")
                except Exception as e:
                    logger.warning(f"8-bit loading failed, using default: {e}")
            
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                **model_kwargs
            )
            
            # Move to appropriate device
            if not model_kwargs.get("load_in_8bit", False):
                model = model.to(self.device)
            
            # Set to evaluation mode
            model.eval()
            
            # Cache the models
            self.models[model_name] = model
            self.tokenizers[model_name] = tokenizer
            
            load_time = time.time() - start_time
            memory_after = self._check_memory_usage()
            
            logger.info(f"Model {model_name} loaded in {load_time:.2f}s")
            logger.debug(f"Memory after loading: {memory_after}")
            
            return model, tokenizer
            
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise
    
    def _generate_response(self, model, tokenizer, prompt: str, 
                          generation_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate response using the model."""
        start_time = time.time()
        
        try:
            # Tokenize input
            inputs = tokenizer.encode(prompt, return_tensors="pt").to(self.device)
            input_length = inputs.shape[1]
            
            # Generation configuration
            gen_config = GenerationConfig(
                max_new_tokens=generation_config.get("max_tokens", 100),
                temperature=generation_config.get("temperature", 0.7),
                top_p=generation_config.get("top_p", 0.9),
                do_sample=generation_config.get("temperature", 0.7) > 0,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
                repetition_penalty=1.1
            )
            
            # Add stop sequences if provided
            stop_sequences = generation_config.get("stop_sequences", [])
            if stop_sequences:
                stop_token_ids = []
                for seq in stop_sequences:
                    tokens = tokenizer.encode(seq, add_special_tokens=False)
                    stop_token_ids.extend(tokens)
                if stop_token_ids:
                    gen_config.eos_token_id = stop_token_ids
            
            # Generate response
            with torch.no_grad():
                outputs = model.generate(
                    inputs,
                    generation_config=gen_config,
                    return_dict_in_generate=True,
                    output_scores=True
                )
            
            # Decode the response
            generated_tokens = outputs.sequences[0][input_length:]
            response_text = tokenizer.decode(generated_tokens, skip_special_tokens=True)
            
            # Clean up response
            response_text = response_text.strip()
            
            # Apply stop sequences manually if needed
            for stop_seq in stop_sequences:
                if stop_seq in response_text:
                    response_text = response_text.split(stop_seq)[0]
            
            processing_time = time.time() - start_time
            tokens_generated = len(generated_tokens)
            
            result = {
                "output": response_text,
                "tokens_generated": tokens_generated,
                "processing_time": processing_time,
                "input_tokens": input_length,
                "tokens_per_second": tokens_generated / processing_time if processing_time > 0 else 0,
                "model_used": model.config.name_or_path if hasattr(model.config, 'name_or_path') else "unknown"
            }
            
            logger.info(f"Generated {tokens_generated} tokens in {processing_time:.2f}s "
                       f"({result['tokens_per_second']:.1f} tokens/s)")
            
            return result
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise
    
    def run_inference(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run inference on a task."""
        try:
            model_name = task_data.get("model", DEFAULT_MODEL)
            input_data = task_data.get("input_data", {})
            
            # Validate input
            prompt = input_data.get("prompt", "")
            if not prompt:
                raise ValueError("No prompt provided")
            
            # Load model
            model, tokenizer = self._load_model(model_name)
            
            # Prepare generation config
            generation_config = {
                "max_tokens": input_data.get("max_tokens", 100),
                "temperature": input_data.get("temperature", 0.7),
                "top_p": input_data.get("top_p", 0.9),
                "stop_sequences": input_data.get("stop_sequences", [])
            }
            
            # Generate response
            result = self._generate_response(model, tokenizer, prompt, generation_config)
            
            # Add metadata
            result["metadata"] = {
                "device": str(self.device),
                "model_name": model_name,
                "memory_usage": self._check_memory_usage(),
                "timestamp": datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Inference failed: {e}")
            return {
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.now().isoformat()
            }
    
    def cleanup_models(self, keep_recent: int = 2):
        """Clean up cached models to free memory."""
        if len(self.models) <= keep_recent:
            return
        
        logger.info(f"Cleaning up models, keeping {keep_recent} most recent")
        
        # Simple cleanup - remove oldest models
        # In a more sophisticated implementation, you'd track usage patterns
        model_names = list(self.models.keys())
        models_to_remove = model_names[:-keep_recent]
        
        for model_name in models_to_remove:
            if model_name in self.models:
                del self.models[model_name]
            if model_name in self.tokenizers:
                del self.tokenizers[model_name]
            
            logger.info(f"Removed cached model: {model_name}")
        
        # Force garbage collection
        import gc
        gc.collect()
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models and system resources."""
        return {
            "loaded_models": list(self.models.keys()),
            "device": str(self.device),
            "memory_usage": self._check_memory_usage(),
            "cache_dir": str(self.cache_dir),
            "torch_version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "cuda_version": torch.version.cuda if torch.cuda.is_available() else None
        }

# Global inference engine instance
inference_engine = ModelInferenceEngine()

def run_inference(task_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Run model inference on given task data."""
    if task_data is None:
        # Placeholder for backward compatibility
        task_data = {
            "model": DEFAULT_MODEL,
            "input_data": {
                "prompt": "Hello, how are you today?",
                "max_tokens": 50,
                "temperature": 0.7
            }
        }
        logger.info("Running inference with default task data")
    
    return inference_engine.run_inference(task_data)

def get_inference_info() -> Dict[str, Any]:
    """Get information about the inference engine."""
    return inference_engine.get_model_info()

def cleanup_inference_cache():
    """Clean up inference engine cache."""
    inference_engine.cleanup_models()
