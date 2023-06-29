import os
from flask import Flask, flash, request, redirect, render_template
from werkzeug.utils import secure_filename

app=Flask(__name__)

app.secret_key = "secret key"
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

path = os.getcwd()
# file Upload
UPLOAD_FOLDER = "/tmp"

if not os.path.isdir(UPLOAD_FOLDER):
    os.mkdir(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


ALLOWED_EXTENSIONS = set(['json'])


import json
import requests
from datetime import datetime

def gh_sesh(user, token):
    s = requests.Session()
    s.auth = (user, token)
    s.headers = {'accept': 'application/vnd.github+json'}
    return s

class GH_Response_Obj:
    def __init__(self, json_all, next_page):
        self.json_all = json_all
        self.next_page = next_page

def gh_get_request(gh_user, gh_token, url):
    s = gh_sesh(gh_user, gh_token)
    response = s.get(url)
    response_status = response.status_code
    if response_status > 200:
        print(f'\n This was the response code: {response_status}')
        exit()

    json = response.json()
    links = response.links

    try:
        next_page = links['next']['url']
    except:
        next_page = None

    full = GH_Response_Obj(json, next_page)

    return full

def gh_post_request(gh_user, gh_token, url, data, new_sync_branch, master_branch_sha):
    s = gh_sesh(gh_user, gh_token)

    headers = {'Authorization': "Token " + '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'}

    response = requests.post('https://api.github.com/repos/far-eye/Superset-Prod-Migration/git/refs', json={
        "ref": "refs/heads/" + new_sync_branch,
        "sha": master_branch_sha
    }, headers=headers)
    
    response_status = response.status_code

    if response_status > 201:
        print(f'\n This was the response code: {response_status}')
        exit()

    json = response.json()

    return json 

def get_branch_sha(gh_user, gh_token, repo_name, branch_name="main"):
    url = f'https://api.github.com/repos/far-eye/{repo_name}/branches/{branch_name}'
    print(url)
    response =gh_get_request(gh_user, gh_token, url)
    sha = response.json_all['commit']['sha']
    return sha

def create_new_branch(gh_user, gh_token, master_branch_sha, new_sync_branch):
	url = f"https://github.com/far-eye/Superset-Prod-Migration/git/refs/heads"
        

	data = {
		"ref": f'refs/heads/{new_sync_branch}',
		"sha": master_branch_sha
	}

	data = json.dumps(data)

	response =gh_post_request(gh_user, gh_token, url, data, new_sync_branch, master_branch_sha)

	return response

def uploadGit(new_sync_branch, dashboard_path):
    from github import Github

    g = Github('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')

    repo = g.get_repo('far-eye/Superset-Prod-Migration')

    with open(dashboard_path, 'r') as file:
        data = file.read()

    repo.create_file('jsonFile/dataset.json', 'upload json', data, branch=new_sync_branch)

def upload(new_sync_branch, dashboard_path):
     headers = {
    'Accept': 'application/vnd.github+json',
    'Authorization': 'Bearer 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',
    'X-GitHub-Api-Version': '2022-11-28',
    'Content-Type': 'application/json',
    }
     
     files = { 
    'formData': (
        dashboard_path, 
        open(dashboard_path, 'rb'), 
        'application/json'
    )
}

     data = '{"message":"my commit message","committer":{"name":"saksham9826","email":"saksham.gupta@getfareye.com"},"content":' + dashboard_path + ',"branch":"' + new_sync_branch + '"}'
     
     response = requests.put('https://api.github.com/repos/far-eye/Superset-Prod-Migration/contents/jsonFile/' + dashboard_path , headers=headers, data=data)

     print(response.json)



def merge_pr(feature):
    import requests

    headers = {
    'Accept': 'application/vnd.github+json',
    'Authorization': 'Bearer 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',
    'X-GitHub-Api-Version': '2022-11-28',
    'Content-Type': 'application/x-www-form-urlencoded',
    }

    data = '{"title":"Amazing new feature","body":"Please pull these awesome changes in!","head":"' + feature + '","base":"main"}'
    print(data)

    response = requests.post('https://api.github.com/repos/far-eye/Superset-Prod-Migration/pulls', headers=headers, data=data)

    print(response.json)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def upload_form():
    return render_template('upload.html')


@app.route('/', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        env = request.form["env"]
        cid = request.form["company_id"]
        emailid = request.form["email_id"]
        

        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No file selected for uploading')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join("/tmp", filename))
            
            flash('File successfully uploaded and gone for validation')


            gh_user = "saksham9826"
            gh_token = "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"
            repo_name = "Superset-Prod-Migration"

            dashboard_path = os.path.join("/tmp", filename)
            
            sha = get_branch_sha(gh_user, gh_token,repo_name)
            now = str(datetime.now()).replace(' ', '__').replace(':', '-').replace('.', '')
            new_sync_branch = f'new_branch_{now}_124'
            new_sync_branch_add = create_new_branch(gh_user, gh_token, sha, new_sync_branch)
            print(new_sync_branch_add)

            uploadGit(new_sync_branch, dashboard_path)
            merge_pr(new_sync_branch)

            return redirect('/')
        else:
            flash('Allowed file types are json')
            return redirect(request.url)


if __name__ == "__main__":
    app.run(host = '0.0.0.0',port = 5000, debug = False)

    # vercel --prod to overcome deployment
    # https://dev.to/yash_makan/4-best-python-web-app-hosting-services-for-freewith-complete-process-57nb