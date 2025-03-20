from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect

# ... решта вашого коду ...

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('chat_room', room_id=1)  # Перенаправлення на чат після входу (можете змінити room_id)
        else:
            return render(request, 'main/login.html', {'form': {'errors': True}})
    return render(request, 'main/login.html')