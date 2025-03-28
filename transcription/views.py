from django.shortcuts import render
from .consumers import agent_audio_data

def agent_audio_view(request):
    context = {
        "audio_data": agent_audio_data
    }
    return render(request, "transcription/agent_audio.html", context)