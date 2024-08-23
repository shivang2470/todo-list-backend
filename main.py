from fastapi import FastAPI, Depends, HTTPException, Request, Header
from typing import Dict
from firebase_admin import credentials, auth, firestore
import firebase_admin
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

cred = credentials.Certificate("constants/serviceAccountKey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
    
@app.get("/")
def read_root():
    return {"message": "Server is running"}

# Function to verify Firebase token from Authorization header
def verify_firebase_token(authorization: str = Header(...)) -> Dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization[len("Bearer "):]  # Extract token after "Bearer "
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except firebase_admin.auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid Firebase token")

@app.post("/todos")
async def add_todo(request: Request, token: dict = Depends(verify_firebase_token)):
    todo_data = await request.json()
    user_id = token['uid']
    todo_ref = db.collection('todos').document()
    todo_ref.set({
        'user_id': user_id,
        'title': todo_data['title'],
        'completed': todo_data['completed']
    })
    return {"id": todo_ref.id, "message": "ToDo added"}

@app.get("/todos")
def get_todos(token: dict = Depends(verify_firebase_token)):
    user_id = token['uid']
    todos_ref = db.collection('todos').where('user_id', '==', user_id)
    todos = []
    for todo in todos_ref.stream():
        todo_data = todo.to_dict()
        todo_data['id'] = todo.id
        todos.append(todo_data)
    return todos

@app.put("/todos")
async def update_todo(todo_id: str, request: Request, token: dict = Depends(verify_firebase_token)):
    todo_data = await request.json()
    if('title' in todo_data):
        db.collection('todos').document(todo_id).update({
            'title': todo_data['title'],
            'completed': todo_data['completed']
        })
    else:
        db.collection('todos').document(todo_id).update({
            'completed': todo_data['completed']
        })
    return {"message": "ToDo updated"}

@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: str, token: str = Depends(verify_firebase_token)):
    db.collection('todos').document(todo_id).delete()
    return {"message": "ToDo deleted"}
