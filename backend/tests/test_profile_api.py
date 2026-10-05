from app.database import SessionLocal
from app.models import User


def register(client,email="profile@example.com",name="Profile Learner",password="Secure123!"):
    response=client.post("/api/auth/register",json={"full_name":name,"email":email,"password":password})
    assert response.status_code==201
    return {"Authorization":"Bearer "+response.json()["access_token"]}


def test_profile_read_update_password_and_deactivate(mysql_client):
    headers=register(mysql_client)

    profile=mysql_client.get("/api/profile",headers=headers)
    assert profile.status_code==200
    assert profile.json()["full_name"]=="Profile Learner"
    assert profile.json()["email"]=="profile@example.com"
    assert "password" not in str(profile.json()).lower()

    updated=mysql_client.put("/api/profile",headers=headers,json={"full_name":"Updated Learner","email":"updated@example.com"})
    assert updated.status_code==200
    assert updated.json()["full_name"]=="Updated Learner"
    assert updated.json()["email"]=="updated@example.com"

    other_headers=register(mysql_client,"other-profile@example.com","Other Learner")
    duplicate=mysql_client.put("/api/profile",headers=headers,json={"full_name":"Updated Learner","email":"other-profile@example.com"})
    assert duplicate.status_code==409

    wrong=mysql_client.put("/api/profile/password",headers=headers,json={"current_password":"WrongPassword!","new_password":"NewSecure123!"})
    assert wrong.status_code==401

    changed=mysql_client.put("/api/profile/password",headers=headers,json={"current_password":"Secure123!","new_password":"NewSecure123!"})
    assert changed.status_code==204

    old_login=mysql_client.post("/api/auth/login",json={"email":"updated@example.com","password":"Secure123!"})
    assert old_login.status_code==401
    new_login=mysql_client.post("/api/auth/login",json={"email":"updated@example.com","password":"NewSecure123!"})
    assert new_login.status_code==200
    new_headers={"Authorization":"Bearer "+new_login.json()["access_token"]}

    wrong_deactivate=mysql_client.post("/api/profile/deactivate",headers=new_headers,json={"current_password":"WrongPassword!"})
    assert wrong_deactivate.status_code==401
    deactivated=mysql_client.post("/api/profile/deactivate",headers=new_headers,json={"current_password":"NewSecure123!"})
    assert deactivated.status_code==204

    assert mysql_client.get("/api/profile",headers=new_headers).status_code==401
    assert mysql_client.post("/api/auth/login",json={"email":"updated@example.com","password":"NewSecure123!"}).status_code==403


def test_profile_delete_requires_confirmation_and_removes_user(mysql_client):
    headers=register(mysql_client,"delete-profile@example.com","Delete Learner")

    bad_confirmation=mysql_client.request("DELETE","/api/profile",headers=headers,json={"current_password":"Secure123!","confirmation":"WRONG"})
    assert bad_confirmation.status_code==422

    wrong_password=mysql_client.request("DELETE","/api/profile",headers=headers,json={"current_password":"WrongPassword!","confirmation":"DELETE"})
    assert wrong_password.status_code==401

    deleted=mysql_client.request("DELETE","/api/profile",headers=headers,json={"current_password":"Secure123!","confirmation":"DELETE"})
    assert deleted.status_code==204

    with SessionLocal() as db:
        assert db.query(User).filter(User.email=="delete-profile@example.com").first() is None

    assert mysql_client.post("/api/auth/login",json={"email":"delete-profile@example.com","password":"Secure123!"}).status_code==401
