from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from pymongo import MongoClient
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import uuid
import os, re, json
from bson import ObjectId

client = MongoClient('mongodb://localhost:27017/')
db = client['proj-manager']
users_collection = db['users']
project_collection = db['projects']

def home(request):
    pb_number = request.session.get('pb_number')
    print(pb_number)
    if pb_number:
        user_data = users_collection.find_one({"pb_number": pb_number})        
    else:
        user_data = None
    print(user_data)
    projects = list(project_collection.find({}).sort("_id", -1))
    projects_with_id = [
        {**project, 'project_id': str(project['_id'])} for project in projects
    ]
    approved_projects = [project for project in projects_with_id if project.get('status') == 'approved']
    pending_projects = [project for project in projects_with_id if project.get('status') != 'approved']

    content = {
        "user": user_data,
        "projects": projects_with_id,
        "approved": approved_projects,
        "pending": pending_projects
    }
    return render(request, 'home.html', content)

def signin(request):
    if request.method == 'POST':
        pb_number = request.POST.get('pb_number')
        password = request.POST.get('password')
        user_data = users_collection.find_one({"pb_number": pb_number})

        if user_data and check_password(password, user_data.get('password')):
            request.session['pb_number'] = pb_number
            request.session['role'] = user_data.get('role').lower()
            return redirect('home')
        else:
            return render(request, 'signin.html', {'error': 'Invalid PB Number or Password'})
    return render(request, 'signin.html')

def signup(request):
    if request.method == 'POST':
        pb_number = request.POST.get('pb_number')
        password = request.POST.get('password')
        name = request.POST.get('name')
        gender = request.POST.get('gender')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        role = request.POST.get('role')
        division = request.POST.get('division')
        department = request.POST.get('department')

        if users_collection.find_one({"pb_number": pb_number}):
            messages.error(request, 'PB Number already exists.')
        else:
            hashed_password = make_password(password)
            user_data = {
                "pb_number": pb_number,
                "password": hashed_password,
                "name": name,
                "gender": gender,
                "phone": phone,
                "email": email,
                "role": role,
                "division": division,
                "department": department,
                "date_joined": datetime.now()
            }
            users_collection.insert_one(user_data)
            messages.success(request, 'Account created successfully. Please sign in.')
            return redirect('signin')

    return render(request, 'signup.html')

def change_password(request):
    if request.method == 'POST':
        pb_number = request.session.get('pb_number')
        old_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')

        user_data = users_collection.find_one({"pb_number": pb_number})

        if user_data and check_password(old_password, user_data.get('password')):
            hashed_new_password = make_password(new_password)
            users_collection.update_one(
                {"pb_number": pb_number},
                {"$set": {"password": hashed_new_password}}
            )
            return redirect('signin')
    return render(request, 'signin.html')

def logout(request):
    request.session.flush() 
    return redirect('home')

def save_uploaded_file(file):
    """Save uploaded file to filesystem and return its path"""
    filename = f"{file.name}"
    
    # Create upload directory if it doesn't exist
    upload_dir = os.path.join('manager','static' ,'project_files')
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save file
    file_path = os.path.join(upload_dir, filename)
    with open(file_path, 'wb+') as destination:
        for chunk in file.chunks():
            destination.write(chunk)
    
    return os.path.join('project_files', filename)

@csrf_exempt
def submit_project(request):
    if request.method == 'POST':
        try:
            # Process form data
            form_data = {
                'name': request.POST.get('name'),
                'pb_number': request.POST.get('pb_number'),
                'division': request.POST.get('division'),
                'project_name': request.POST.get('project_name'),
                'description': request.POST.get('description'),
                'category': request.POST.get('category'),
                'tools_used': [t.strip() for t in request.POST.get('tools_used', '').split(',') if t.strip()],
                'benefits': request.POST.get('benefits'),
                'submitted_date': datetime.now(),
                'status': 'pending'
            }
            
            # Process dates if provided
            if request.POST.get('start_date'):
                form_data['start_date'] = datetime.strptime(request.POST.get('start_date'), '%Y-%m-%d')
            if request.POST.get('end_date'):
                form_data['end_date'] = datetime.strptime(request.POST.get('end_date'), '%Y-%m-%d')
            
            # Process file uploads - ensure we're getting multiple files
            uploaded_files = request.FILES.getlist('files')  # This should get all files
            file_paths = []
            
            print(f"Received {len(uploaded_files)} files")  # Debugging
            
            for file in uploaded_files:
                print(f"Processing file: {file.name} ({file.size} bytes)")  # Debugging
                if file.size > 50 * 1024 * 1024:  # 50MB limit
                    print(f"File {file.name} exceeds size limit")
                    continue
                
                try:
                    file_path = save_uploaded_file(file)
                    file_paths.append({
                        'path': file_path,
                        'name': file.name,
                        'size': file.size,
                        'content_type': file.content_type,
                    })
                    print(f"Saved file: {file_path}")  # Debugging
                except Exception as e:
                    print(f"Failed to save file {file.name}: {str(e)}")
                    continue
            
            if file_paths:
                form_data['files'] = file_paths
                print(f"Added {len(file_paths)} files to project data")  # Debugging
            
            # Insert into MongoDB
            result = project_collection.insert_one(form_data)
            print(f"Inserted project with ID: {result.inserted_id}")  # Debugging
            
            return JsonResponse({
                'message': 'Project submitted successfully',
                'project_id': str(result.inserted_id),
                'files_received': len(uploaded_files),
                'files_saved': len(file_paths)
            }, status=201)
            
        except Exception as e:
            print(f"Error submitting project: {str(e)}")
            return JsonResponse({
                'error': str(e),
                'message': 'Failed to submit project'
            }, status=500)
    
    return JsonResponse({
        'error': 'Invalid request method',
        'message': 'Only POST requests are allowed'
    }, status=405)

def approve(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            project_id = data.get('project_id')
            project_collection.update_one(
                {"_id": ObjectId(project_id)},
                {"$set": {"status": "approved",
                    "approved_date": datetime.now()
                }}
            )
            return JsonResponse({"success": True, "message": "Project approved successfully."})
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)})
    
    return JsonResponse({"success": False, "message": "Invalid request method."})

def reject(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            project_id = data.get('project_id')
            project_collection.delete_one(
                {"_id": ObjectId(project_id)}
            )
            return JsonResponse({"success": True, "message": "Project rejected successfully."})
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)})
    return JsonResponse({"success": False, "message": "Invalid request method."})