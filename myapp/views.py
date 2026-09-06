from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, JsonResponse,HttpResponse
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import TokenStorePC, GeneratedToken
from .serializers import TokenStoreSerializer
import uuid
import io
import os
import redis
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
from collections import Counter, defaultdict
from io import BytesIO
import base64
import datetime
import re
import random
from django.core.mail import send_mail
from django.contrib.auth.models import User
import json
from django.views.decorators.csrf import csrf_exempt
import requests
from django.http import JsonResponse
import base64
from reportlab.pdfgen import canvas
from io import BytesIO
from django.core.mail import EmailMessage
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


# Initialize Redis connection
redis_client = redis.StrictRedis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB
)

@api_view(['POST'])
def submit_token(request):
    email = request.data.get('email')
    token = request.data.get('token')
    if token and email:
        if GeneratedToken.objects.filter(email=email, token=token).exists():
            serializer = TokenStoreSerializer(data={'email': email, 'token': token})
            if serializer.is_valid():
                serializer.save()
                return Response({"status": "success", "message": "Token stored successfully"}, status=status.HTTP_200_OK)
        return Response({"status": "error", "message": "Invalid token data"}, status=status.HTTP_400_BAD_REQUEST)
    return Response({"status": "error", "message": "Token not provided"}, status=status.HTTP_400_BAD_REQUEST)

def loginpage(request):
    if request.method == "POST":
        if 'l1' in request.POST:
            username = request.POST.get('username')
            password = request.POST.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')
            messages.error(request, "Invalid Credentials")
        elif 's1' in request.POST:
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')
            if not User.objects.filter(username=username).exists() and not User.objects.filter(email=email).exists():
                user = User.objects.create_user(username, email, password)
                user.save()
                messages.success(request, "Account created successfully!")
                login(request, user)
                return redirect('home')
            messages.error(request, "Username or Email already exists.")
    return render(request, 'loginpage.html')

@login_required
def user_logout(request):
    logout(request)
    return redirect('loginpage')
    
# forget password 
def forgotpass(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "No account found with this email.")
            return redirect("forgotpass")

        otp = str(random.randint(100000, 999999))

        try:
            send_mail(
                subject="TrackMyLogs - Password Reset OTP",
                message=f"Your OTP for password reset is: {otp}",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
                fail_silently=False
            )

            # Store OTP in session only after email is sent successfully
            request.session["reset_email"] = email
            request.session["reset_username"] = user.username
            request.session["reset_otp"] = otp

            messages.success(request, "OTP sent to your email.")
            return redirect("verify_otp")

        except Exception as e:
            print("PASSWORD RESET EMAIL ERROR:", repr(e))
            messages.error(
                request,
                "Unable to send the OTP email. Please try again."
            )
            return redirect("forgotpass")

    return render(request, "forgotpass.html")


# verify otp 

def verify_otp(request):
    if request.method == "POST":
        entered_otp = request.POST.get("otp")
        session_otp = request.session.get("reset_otp")

        if entered_otp == session_otp:
            request.session["otp_verified"] = True
            return redirect("reset_password")
        else:
            messages.error(request, "Invalid OTP.")
            return redirect("verify_otp")

    return render(request, "verify_otp.html")


@login_required
def home(request):
    if request.method == "POST" and 'GAT' in request.POST:
        return redirect('GetAuthenticationToken')
    return render(request, 'home.html')

@login_required
def GetAuthenticationToken(request):
    user = request.user
    try:
        existing_token = GeneratedToken.objects.get(username=user.username)
        message = "You have already generated a token. Check your profile to get your authentication token."
        return render(request, 'GetAuthenticationToken.html', {
            'message': message,
            'authentication_token': existing_token.token,
            'username': user.username,
            'email': user.email,
        })
    except GeneratedToken.DoesNotExist:
        authentication_token = uuid.uuid4()
        GeneratedToken.objects.create(
            username=user.username,
            email=user.email,
            token=authentication_token
        )
        return render(request, 'GetAuthenticationToken.html', {
            'authentication_token': authentication_token,
            'username': user.username,
            'email': user.email,
        })

@login_required
def profile(request):
    user = request.user
    authentication_token = GeneratedToken.objects.filter(username=user.username).first()
    return render(request, 'profile.html', {'user': user, 'authentication_token': authentication_token.token if authentication_token else None})

@login_required
def download_script(request):
    exe_path = os.path.join(settings.BASE_DIR, 'dist', 'TrackMyLogs.exe')
    return FileResponse(open(exe_path, 'rb'), as_attachment=True, filename='TrackMyLogs.exe')

def reset_password_view(request):
    if not request.session.get("otp_verified"):
        messages.error(request, "OTP verification required.")
        return redirect("forgotpass")

    if request.method == "POST":
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("reset_password")

        email = request.session.get("reset_email")  # Retrieve email from session
        if not email:
            messages.error(request, "Session expired. Try again.")
            return redirect("forgotpass")

        try:
            user = User.objects.get(email=email)  # Fetch user using email
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect("forgotpass")

        user.set_password(new_password)
        user.save() 

        messages.success(request, "Password reset successfully.")
        request.session.flush()
        return redirect("loginpage")

    return render(request, "resetpass.html")

def log_list(request):
    email = request.GET.get('email')
    if not email:
        return render(request, 'log_list.html', {'error': 'Email parameter is required'})
    logs = redis_client.lrange(f"email:{email}", 0, -1)
    return render(request, 'log_list.html', {'logs': [log.decode('utf-8') for log in logs]})

logs = []  # Global variable to store logs
def fetch_logs(request):
    email = request.GET.get('email')
    if not email:
        return JsonResponse({'error': 'Email parameter is required'}, status=400)

    redis_key = f"email:{email}"
    logs = redis_client.lrange(redis_key, 0, -1)

    if not logs:
        return JsonResponse({'error': 'No logs found'}, status=404)

    return JsonResponse({'logs': logs})  # No need to decode, as logs are already strings


def terms_of_service(request):
    return render(request, 'terms_of_service.html')

def privacy_policy(request):
    return render(request, 'privacy_policy.html')

def contact(request):
    return render(request, 'contact.html')


# Connect to Redis
redis_client = redis.StrictRedis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True
)

@login_required
def analysis(request):
    return render(request, 'analysis.html')
 

def fetch_analysis_data(request):
    email = request.GET.get('email')
    
    # If no email in GET request, use the email from the authenticated user
    if not email:
        email = request.user.email
        
    redis_key = f"email:{email}"
    logs = redis_client.lrange(redis_key, 0, -1)
    
    if not logs:
        return JsonResponse({'error': 'No logs found'}, status=404)
    
    # Data structures to hold parsed data
    log_types = []
    app_usage = defaultdict(int)
    app_timestamps = []      # Timestamps for "Opened App" logs
    cpu_timestamps = []      # Timestamps for "Hardware Usage Information" logs
    cpu_usages = []          # CPU usage values from hardware logs
    network_status = defaultdict(int)
    local_ips = defaultdict(int)
    remote_ips = defaultdict(int)
    
    for i, log in enumerate(logs):
        parts = log.split(': ')
        if len(parts) < 2:
            continue
        log_type = parts[0]
        log_types.append(log_type)
        log_message = ': '.join(parts[1:])
        
        # Try to extract a timestamp from the log.
        ts = None
        if " at " in log:
            timestamp_str = log.split(" at ")[-1].strip()
            try:
                ts = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            except Exception:
                ts = None

        # Opened App logs: extract app name and timestamp
        if log_type == "Opened App":
            match = re.search(r"App: ['\"](.*?)['\"]", log_message)
            if match:
                app_name = match.group(1)
                app_usage[app_name] += 1
            else:
                app_usage["Unknown"] += 1
            if ts:
                app_timestamps.append(ts)
        
        # Hardware Usage Information: extract CPU usage
        if log_type == "Hardware Usage Information":
            if ts:
                match_cpu = re.search(r"CPU Usage: (\d+\.\d+)%", log_message)
                if match_cpu:
                    cpu_val = float(match_cpu.group(1))
                    cpu_timestamps.append(ts)
                    cpu_usages.append(cpu_val)
        
        # Network Activity Information: extract network status, local and remote IPs
        if log_type == "Network Activity Information":
            # Extract network status: assume it comes after ", Status: "
            try:
                status_part = log_message.split(", Status: ")[-1]
                status = status_part.split(" at ")[0].strip()
                network_status[status] += 1
            except Exception:
                pass
            # Extract local IP
            try:
                local_part = log_message.split("Local: addr(")[1]
                local_info = local_part.split(")")[0]
                if "ip=" in local_info:
                    local_ip = local_info.split("ip=")[1].split(",")[0].strip("'\"")
                else:
                    local_ip = local_info.strip()
                local_ips[local_ip] += 1
            except Exception:
                pass
            # Extract remote IP, if available
            try:
                if "Remote: addr(" in log_message:
                    remote_part = log_message.split("Remote: addr(")[1]
                    remote_info = remote_part.split(")")[0]
                    if "ip=" in remote_info:
                        remote_ip = remote_info.split("ip=")[1].split(",")[0].strip("'\"")
                    else:
                        remote_ip = remote_info.strip()
                    remote_ips[remote_ip] += 1
            except Exception:
                pass

    # Create graphs
    # Graph 1: Log Type Distribution (Bar Chart)
    fig1, ax1 = plt.subplots(figsize=(8, 5))
    log_counts = Counter(log_types)
    ax1.bar(list(log_counts.keys()), list(log_counts.values()), color='skyblue')
    ax1.set_xlabel('Log Type')
    ax1.set_ylabel('Count')
    ax1.set_title('Log Type Distribution')
    ax1.set_xticks(range(len(log_counts)))
    ax1.set_xticklabels(list(log_counts.keys()), rotation=45, ha='right')
    
    # Graph 2: Application Usage Count (Bar Chart)
    fig2, ax2 = plt.subplots(figsize=(8, 5))
    if app_usage:
        ax2.bar(list(app_usage.keys()), list(app_usage.values()), color='lightgreen')
        ax2.set_xlabel('Application')
        ax2.set_ylabel('Usage Count')
        ax2.set_title('Application Usage Count')
        ax2.set_xticks(range(len(app_usage)))
        ax2.set_xticklabels(list(app_usage.keys()), rotation=45, ha='right')
    else:
        ax2.text(0.5, 0.5, 'No application usage data available', ha='center', va='center', fontsize=12)
    
    # Graph 3: Log Type Distribution (Pie Chart)
    fig3, ax3 = plt.subplots(figsize=(8, 5))
    if log_counts:
        wedges, texts, autotexts = ax3.pie(
        list(log_counts.values()),
        autopct='%1.1f%%',
        startangle=90,
        colors=['gold', 'lightcoral', 'deepskyblue', 'limegreen'],
        textprops={'fontsize': 8}  # Reduce label font size
    )
        # Move labels to a vertical legend
        ax3.legend(
        wedges,
        log_counts.keys(),
        title="Log Types",
        loc="center left",
        bbox_to_anchor=(1, 0.5),
        fontsize=8
    )
    else:
        ax3.text(0.5, 0.5, 'No log data available', ha='center', va='center', fontsize=12)
    fig3.tight_layout()
    
    # Graph 4: Top 5 Most Opened Apps (Horizontal Bar Chart)
    fig4, ax4 = plt.subplots(figsize=(8, 5))
    if app_usage:
        top_apps = dict(Counter(app_usage).most_common(5))
        ax4.barh(list(top_apps.keys()), list(top_apps.values()), color='purple')
        ax4.set_xlabel('Usage Count')
        ax4.set_ylabel('Application')
        ax4.set_title('Top 5 Most Opened Apps')
    else:
        ax4.text(0.5, 0.5, 'No application usage data available', ha='center', va='center', fontsize=12)
    
    # Graph 5: Application Usage Over Time (Line Chart)
    fig5, ax5 = plt.subplots(figsize=(8, 5))
    if app_timestamps:
        sorted_app_ts = sorted(app_timestamps)
        usage_over_time = list(range(1, len(sorted_app_ts) + 1))
        ax5.plot(sorted_app_ts, usage_over_time, marker='o', linestyle='-', color='red', label='App Usage')
        ax5.set_xlabel('Timestamp')
        ax5.set_ylabel('Cumulative Usage Count')
        ax5.set_title('Application Usage Over Time')
        ax5.legend()
    else:
        ax5.text(0.5, 0.5, 'No timestamped app data available', ha='center', va='center', fontsize=12)
    
    # Graph 6: CPU Usage Over Time (Line Chart)
    fig6, ax6 = plt.subplots(figsize=(8, 5))
    if cpu_timestamps and cpu_usages:
        sorted_cpu = sorted(zip(cpu_timestamps, cpu_usages), key=lambda x: x[0])
        sorted_cpu_ts, sorted_cpu_vals = zip(*sorted_cpu)
        ax6.plot(sorted_cpu_ts, sorted_cpu_vals, marker='s', linestyle='--', color='blue', label='CPU Usage')
        ax6.set_xlabel('Timestamp')
        ax6.set_ylabel('CPU Usage (%)')
        ax6.set_title('CPU Usage Over Time')
        ax6.legend()
    else:
        ax6.text(0.5, 0.5, 'No CPU usage data available', ha='center', va='center', fontsize=12)
    
    # Graph 7: Network Status Distribution (Pie Chart)
    fig7, ax7 = plt.subplots(figsize=(8, 5))
    if network_status:
        wedges, texts, autotexts = ax7.pie(
        list(network_status.values()),
        autopct='%1.1f%%',
        startangle=90,
        colors=['violet', 'lightblue', 'orange', 'yellow'],
        textprops={'fontsize': 8}  # Reduce label font size
        )
        ax7.set_title('Network Status Distribution', fontsize=10)

    # Move labels to a vertical legend
        ax7.legend(
        wedges,
        network_status.keys(),
        title="Network Status",
        loc="center left",
        bbox_to_anchor=(1, 0.5),
        fontsize=8
    )
    else:
        ax7.text(0.5, 0.5, 'No network status data available',
                 ha='center', va='center', fontsize=12)
    fig7.tight_layout()

    # Graph 8: Top 5 Local IP Addresses (Bar Chart)
    fig8, ax8 = plt.subplots(figsize=(8, 5))
    if local_ips:
        top_local = dict(Counter(local_ips).most_common(5))
        ax8.bar(list(top_local.keys()), list(top_local.values()), color='teal')
        ax8.set_xlabel('Local IP Address')
        ax8.set_ylabel('Count')
        ax8.set_title('Top 5 Local IP Addresses')
        ax8.set_xticks(range(len(top_local)))
        ax8.set_xticklabels(list(top_local.keys()), rotation=45, ha='right')
    else:
        ax8.text(0.5, 0.5, 'No local IP data available', ha='center', va='center', fontsize=12)
    
    # Graph 9: Top 5 Remote IP Addresses (Bar Chart)
    fig9, ax9 = plt.subplots(figsize=(8, 5))
    if remote_ips:
        top_remote = dict(Counter(remote_ips).most_common(5))
        ax9.bar(list(top_remote.keys()), list(top_remote.values()), color='brown')
        ax9.set_xlabel('Remote IP Address')
        ax9.set_ylabel('Count')
        ax9.set_title('Top 5 Remote IP Addresses')
        ax9.set_xticks(range(len(top_remote)))
        ax9.set_xticklabels(list(top_remote.keys()), rotation=45, ha='right')
    else:
        ax9.text(0.5, 0.5, 'No remote IP data available', ha='center', va='center', fontsize=12)
    
    # Convert figure to base64
    def plot_to_base64(fig):
        buffer = BytesIO()
        fig.savefig(buffer, format='png', bbox_inches='tight')
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    graphs = {
        'log_distribution': plot_to_base64(fig1),
        'app_usage': plot_to_base64(fig2),
        'log_pie_chart': plot_to_base64(fig3),
        'top_opened_apps': plot_to_base64(fig4),
        'app_usage_over_time': plot_to_base64(fig5),
        'cpu_usage_over_time': plot_to_base64(fig6),
        'network_status_distribution': plot_to_base64(fig7),
        'top_local_ips': plot_to_base64(fig8),
        'top_remote_ips': plot_to_base64(fig9),
    }
    
    plt.close('all')
    return JsonResponse(graphs)

def create_pdf_with_graphs(graphs):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Header/Footer function
    def add_header_footer():
        # Add Logo Image in the Header (only on the first page)
        logo_path = 'weblogs/static/img/logo.png'
        try:
            c.drawImage(logo_path, 50, height - 40, width=80, height=40, preserveAspectRatio=True, anchor='n')
        except Exception as e:
            print(f"Error loading logo image: {e}")

        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawString((width - c.stringWidth("TrackMyLogs", "Helvetica-Bold", 16)) / 2, height - 40, "TrackMyLogs")
        # Footer
        c.setFont("Helvetica", 10)
        c.drawString(width - 80, 20, f"Page {c.getPageNumber()}")

    # --- Introductory Page ---
    add_header_footer()
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 120, "Welcome to Your TrackMyLogs Report")

    c.setFont("Helvetica", 12)
    intro_text = (
        "Thank you for choosing TrackMyLogs!\n\n"
        "This report presents a clear overview of your recent system activity and log records.\n "
        "Regularly reviewing your logs helps you stay informed about your system’s behavior \nand performance.\n\n"
        "TrackMyLogs is designed to make complex data simple and actionable. "
        "\nWith these visual summaries, you can:\n"
        "• Gain insights into your daily operations\n"
        "• Detect patterns and anomalies at a glance\n"
        "• Make confident, data-driven decisions\n\n"
        "We hope this report helps you take control of your system’s health and performance."
    )
    text_object = c.beginText(70, height - 170)
    for line in intro_text.split('\n'):
        text_object.textLine(line)
    c.drawText(text_object)

    c.showPage()  # Move to the next page for graphs

    # --- Graph Pages ---
    margin_x = 60
    image_width = width - 2 * margin_x
    image_height = 220
    label_gap = 20
    section_gap = 40
    y_position = height - 80  # Start below header

    add_header_footer()

    for graph_name, base64_image_data in graphs.items():
        # Start a new page if needed
        if y_position < image_height + label_gap + section_gap:
            c.showPage()
            add_header_footer()
            y_position = height - 80

        # Draw graph label/title
        c.setFont("Helvetica-Bold", 13)
        label_text = graph_name.replace('_', ' ').title()
        c.drawString(margin_x, y_position, label_text)
        y_position -= label_gap

        # Draw graph image
        try:
            img_data = base64.b64decode(base64_image_data)
            img_buffer = BytesIO(img_data)
            image = ImageReader(img_buffer)
            c.drawImage(
                image,
                margin_x, y_position - image_height,
                width=image_width, height=image_height,
                preserveAspectRatio=True, anchor='n'
            )
        except Exception as e:
            c.setFont("Helvetica", 10)
            c.setFillColorRGB(1, 0, 0)
            c.drawString(margin_x, y_position - 20, f"Failed to load image: {e}")
            c.setFillColorRGB(0, 0, 0)

        y_position -= image_height + section_gap

    c.save()
    buffer.seek(0)
    return buffer

def send_email_with_pdf(user_email, subject, body, pdf_buffer):
    try:
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=user_email,  # Send from the user's email
            to=[user_email],
        )
        email.attach('report.pdf', pdf_buffer.read(), 'application/pdf')
        email.send()
        print(f"Email sent successfully to {user_email}")
    except Exception as e:
        print(f"Error sending email: {e}")

def fetch_data_from_api(user_email):
    try:
        url = f'http://127.0.0.1:8000/api/fetch-analysis-data/?email={user_email}'
        headers = {'Accept': 'application/json'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print("Exception:", e)
    return None

@csrf_exempt
def close_event(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print("Received close event:", data)
            user_email = data.get('email')
            
            mail_data = fetch_data_from_api(user_email)
            print("Fetched data from API:", mail_data)
            
            if mail_data:
                graphs = {
                    'log_distribution': mail_data.get('log_distribution'),
                    'app_usage': mail_data.get('app_usage'),
                    'log_pie_chart': mail_data.get('log_pie_chart'),
                    'top_opened_apps': mail_data.get('top_opened_apps'),
                    'app_usage_over_time': mail_data.get('app_usage_over_time'),
                    'cpu_usage_over_time': mail_data.get('cpu_usage_over_time'),
                    'network_status_distribution': mail_data.get('network_status_distribution'),
                    'top_local_ips': mail_data.get('top_local_ips'),
                    'top_remote_ips': mail_data.get('top_remote_ips'),
                }
                
                graphs = {name: base64_data for name, base64_data in graphs.items() if base64_data}
                
                if graphs:
                    pdf_buffer = create_pdf_with_graphs(graphs)
                    subject = "Your Report"
                    body = "Attached is your performance report with all the graphs."
                    send_email_with_pdf(user_email, subject, body, pdf_buffer)
                else:
                    print("No valid graphs to include in the report.")
            else:
                print("No data received from the API.")

            # Cleanup Redis
            redis_key = f"email:{user_email}"
            redis_client.delete(redis_key)
            print(f"Redis data cleared for email: {user_email}")
            
            return JsonResponse({"status": "success", "message": "Close event received"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)