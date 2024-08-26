from dotenv import load_dotenv
import os
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
import yt_dlp  # Replacing pytube with yt-dlp for YouTube downloads
import assemblyai as aai
from django.conf import settings
import google.generativeai as genai
from .models import BlogPost
load_dotenv()
 
 

@login_required
def index(request):
    return render(request, 'index.html')



@csrf_exempt
def generate_blog(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)  # json to dict
            yt_link = data['link']
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({'error': 'Invalid data sent'}, status=400)

        # Steps:
        # 1. Get YouTube title
        title = yt_title(yt_link)

        # 2. Get transcript using AssemblyAI
        transcription = get_transcription(yt_link)
        if not transcription:
            return JsonResponse({'error': 'Failed to get transcript'}, status=500)

        # 3. Generate blog
        blog_content,formatted_content = generate_blog_from_transcription(transcription)
        if not blog_content:
            return JsonResponse({'error': 'Failed to generate blog article'}, status=500)
        # 4. Save blog article
        new_blog_article = BlogPost.objects.create(
            user = request.user,
            yt_title =  title,
            yt_link = yt_link , 
            generated_content = blog_content, 
            formated_content = formatted_content,
        )
        # print(f"User: {request.user}, Title: {title}, Link: {yt_link}, Content: {formatted_content}")
        new_blog_article.save()


        # 5. Return blog article as a response
        return JsonResponse({'content': formatted_content})
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)


def blog_details(request,pk ):
    blog_article_detail = BlogPost.objects.get(id=pk)
    if request.user == blog_article_detail.user:
        return render(request,'blog-details.html',{'blog_article_detail':blog_article_detail})
    else:
        return redirect('/')
     



def blog_list(request):
    blog_articles = BlogPost.objects.filter(user = request.user)
    return render(request,'all-blogs.html',{'blog_articles':blog_articles})



def yt_title(link):
    ydl_opts = {
        'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(link, download=False)
        title = info_dict.get('title', None)
    return title

 

def generate_blog_from_transcription(transcription):
    google_api_key = os.getenv('GOOGLE_API_KEY')
    genai.configure(api_key=google_api_key)
    model = genai.GenerativeModel(model_name="gemini-1.5-flash")

    # First prompt: Generate the blog article content
    blog_prompt = (
        "Using the provided transcript, create a comprehensive blog article. "
        "The article should include the following components:\n"
        "1. A catchy and relevant title.\n"
        "2. An engaging introductory paragraph that provides an overview of the content.\n"
        "3. Subheadings that clearly define different sections of the article.\n"
        "4. Content under each subheading that expands on the points made in the transcript, with examples or analogies where applicable.\n"
        "5. A conclusion that summarizes the key points and suggests further reading or action.\n"
        "6. The total word count should not exceed 2500 words.\n"
        
        "Example Layout:\n"
        "Title: The Importance of Time Management for Students\n"
        "Introduction: Time management is an essential skill for students, allowing them to balance academic responsibilities with personal life...\n"
        "Subheading: Understanding the Importance of Time Management\n"
        "Content: Effective time management helps students prioritize tasks, meet deadlines, and reduce stress...\n"
        "Conclusion: In conclusion, mastering time management is key to a successful and balanced student life...\n\n"
        
        f"Transcript:\n{transcription}\n\n"
        "Generate the blog content based on this structure."
    )


    response = model.generate_content(blog_prompt)
    blog_content = response.text
     
    # Second prompt: Format the content with HTML tags
    formatting_prompt = (
        "Analyze the following blog article text and format it using appropriate HTML tags. "
        "Structure the content based on its natural flow and context:\n"
        "1. Identify the main title and format it using a suitable heading tag, ensuring it's bold and centered using inline CSS.\n"
        "2. Recognize subheadings and apply the appropriate heading tags.\n"
        "3. Format paragraphs, lists, and other text elements as necessary.\n"
        "4. Apply inline styles like bold, italic, or underlining where relevant.\n"
        
        "Example formatting:\n"
        "<h1 style=\"text-align: center; font-weight: bold;\">The Importance of Time Management for Students</h1>\n"
        "<h2>Understanding the Importance of Time Management</h2>\n"
        "<p>Effective time management helps students prioritize tasks, meet deadlines, and reduce stress...</p>\n\n"
        
        f"Blog Article:\n{blog_content}\n\n"
        "Format the content using these HTML elements, ensuring that the structure is coherent and visually appealing."
    )


    formatted_response = model.generate_content(formatting_prompt)
    formatted_content = formatted_response.text

    return blog_content,formatted_content


def download_audio(link):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(settings.MEDIA_ROOT, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(link, download=True)
        file_name = ydl.prepare_filename(info_dict)
        base, ext = os.path.splitext(file_name)
        mp3_file = base + '.mp3'

    return mp3_file



def get_transcription(link):
    audio_file = download_audio(link)
    aai.settings.api_key = os.getenv('ASSEMBLY_API_KEY')
    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_file)
    # print(transcript.text)
    return transcript.text




def user_login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            error_message = "Invalid username or password"
            return render(request, 'login.html', {"error_message": error_message})
    return render(request, 'login.html')




def user_signup(request):
    if request.method == "POST":
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        repeatpassword = request.POST['repeatpassword']

        if password == repeatpassword:
            try:
                user = User.objects.create_user(username, email, password)
                user.save()
                login(request, user)
                return redirect('/')
            except:
                error_message = "Error creating account"
                return render(request, 'signup.html', {"error_message": error_message})
        else:
            error_message = "Passwords do not match"
            return render(request, 'signup.html', {"error_message": error_message})
    return render(request, 'signup.html')




def user_logout(request):
    logout(request)
    return redirect('/')
