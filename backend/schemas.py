from pydantic import BaseModel
from typing import Optional

class RegisterRequest(BaseModel):
    user_id: str
    password: str
    
class LoginRequest(BaseModel):
    user_id: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    role: str

class UserResponse(BaseModel):
    id: str
    user_id: str
    role: str
    created_at: str

class SessionResponse(BaseModel):
    id: str
    room_code: str
    completion_key: str
    language: str
    total_players: int
    num_human_players: int
    discussion_duration: int
    voting_duration: int
    completed_at: str
    payment_status: str
    payment_amount: Optional[float]
    claimed_at: Optional[str]
    stats_file_path: str

class MTurkRegisterRequest(BaseModel):
    worker_id: str
    assignment_id: str
    hit_id: str

class MTurkPaymentRequest(BaseModel):
    session_id: str


