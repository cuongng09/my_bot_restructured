import os
from pathlib import Path

# 1. Patch pytorch_backend.py
backend_file = Path("/app/backend/backends/pytorch_backend.py")
if backend_file.exists():
    content = backend_file.read_text(encoding="utf-8")
    old_init = 'def __init__(self, model_size: str = "base"):'
    new_init = '''def __init__(self, model_size: str = None):
        import os
        env_m = os.getenv("WHISPER_MODEL") or os.getenv("VOICEBOX_MODEL") or "medium"
        model_size = (model_size or env_m).lower().replace("whisper-", "").strip()'''
    if old_init in content:
        content = content.replace(old_init, new_init)
        backend_file.write_text(content, encoding="utf-8")
        print("Patched pytorch_backend.py successfully")
    else:
        print("pytorch_backend.py already patched or init signature not found")

# 2. Patch main.py
main_file = Path("/app/backend/main.py")
if main_file.exists():
    content = main_file.read_text(encoding="utf-8")
    
    # Allow model parameter in transcribe endpoint
    old_endpoint = 'async def transcribe_audio(\n    file: UploadFile = File(...),\n    language: Optional[str] = Form(None),\n):'
    new_endpoint = 'async def transcribe_audio(\n    file: UploadFile = File(...),\n    language: Optional[str] = Form(None),\n    model: Optional[str] = Form(None),\n):'
    
    if old_endpoint in content:
        content = content.replace(old_endpoint, new_endpoint)
        print("Patched transcribe_audio endpoint arguments")

    # Update model resolution inside transcribe_audio
    old_logic = '''        # Check if Whisper model is downloaded (uses default size "base")
        model_size = whisper_model.model_size
        model_name = f"openai/whisper-{model_size}"'''

    new_logic = '''        # Check if Whisper model is downloaded
        import os
        env_m = os.getenv("WHISPER_MODEL") or os.getenv("VOICEBOX_MODEL") or "medium"
        req_model = (model or whisper_model.model_size or env_m).lower().replace("whisper-", "").strip()
        model_size = req_model
        model_name = f"openai/whisper-{model_size}"'''

    if old_logic in content:
        content = content.replace(old_logic, new_logic)
        print("Patched model resolution logic in transcribe_audio")

    # Ensure model is loaded with model_size
    old_transcribe = '        text = await whisper_model.transcribe(tmp_path, language)'
    new_transcribe = '''        if not whisper_model.is_loaded() or whisper_model.model_size != model_size:
            await whisper_model.load_model_async(model_size)
        text = await whisper_model.transcribe(tmp_path, language)'''

    if old_transcribe in content and new_transcribe not in content:
        content = content.replace(old_transcribe, new_transcribe)
        print("Patched load_model_async check before transcription")

    # Don't swallow HTTPException into 500
    old_except = '''    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))'''
    new_except = '''    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))'''

    if old_except in content:
        content = content.replace(old_except, new_except)
        print("Patched HTTPException handling in transcribe_audio")

    main_file.write_text(content, encoding="utf-8")
    print("Patched main.py successfully")
