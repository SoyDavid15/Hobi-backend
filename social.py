import os
from datetime import date, datetime, timedelta
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from supabase import create_client
from hobbies import get_current_user, supabase_admin

load_dotenv()

router = APIRouter(prefix="", tags=["social"])


class AddFriendRequest(BaseModel):
    friend_code: str = Field(..., min_length=5)


class RespondFriendRequest(BaseModel):
    friendship_id: str = Field(..., min_length=5)
    action: str = Field(..., pattern="^(accept|reject)$")


class CreateGroupRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    friend_ids: list[str] = Field(..., min_length=1)  # user IDs of friends to invite


@router.get("/profile")
def get_user_profile(user_id: str = Depends(get_current_user)):
    res = supabase_admin.table("profiles").select("*").eq("id", user_id).maybe_single().execute()
    if not res or not res.data:
        # Create profile if missing
        import random
        new_code = f"HOBI-{random.randint(100000, 999999)}"
        ins = supabase_admin.table("profiles").insert({"id": user_id, "friend_code": new_code, "username": f"User_{user_id[:4]}"}).execute()
        if ins and ins.data:
            return ins.data[0]
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    return res.data


@router.get("/friends")
def get_friends(user_id: str = Depends(get_current_user)):
    # Get friendships where user is user_id or friend_id
    res1 = supabase_admin.table("friendships").select("id, status, user_id, friend_id, created_at").eq("user_id", user_id).execute()
    res2 = supabase_admin.table("friendships").select("id, status, user_id, friend_id, created_at").eq("friend_id", user_id).execute()

    friendships = []
    if res1 and res1.data:
        friendships.extend(res1.data)
    if res2 and res2.data:
        friendships.extend(res2.data)

    # Collect all unique user IDs involved
    other_ids = set()
    for f in friendships:
        other_ids.add(f["friend_id"] if f["user_id"] == user_id else f["user_id"])

    profiles_map = {}
    if other_ids:
        p_res = supabase_admin.table("profiles").select("id, username, friend_code").in_("id", list(other_ids)).execute()
        if p_res and p_res.data:
            for p in p_res.data:
                profiles_map[p["id"]] = p

    formatted_friends = []
    for f in friendships:
        other_id = f["friend_id"] if f["user_id"] == user_id else f["user_id"]
        profile = profiles_map.get(other_id, {"id": other_id, "username": "Desconocido", "friend_code": ""})
        formatted_friends.append({
            "friendship_id": f["id"],
            "status": f["status"],
            "is_incoming": f["friend_id"] == user_id and f["status"] == "pending",
            "is_outgoing": f["user_id"] == user_id and f["status"] == "pending",
            "friend": profile,
            "created_at": f["created_at"]
        })

    return {"friends": formatted_friends}


@router.post("/friends/add")
def add_friend(body: AddFriendRequest, user_id: str = Depends(get_current_user)):
    code = body.friend_code.strip().upper()
    # Find profile by friend_code
    p_res = supabase_admin.table("profiles").select("id").eq("friend_code", code).maybe_single().execute()
    if not p_res or not p_res.data:
        raise HTTPException(status_code=404, detail="Código de amigo no encontrado")
    
    friend_id = p_res.data["id"]
    if friend_id == user_id:
        raise HTTPException(status_code=400, detail="No puedes agregarte a ti mismo")

    # Check existing friendship
    existing = (
        supabase_admin.table("friendships")
        .select("*")
        .or_(f"and(user_id.eq.{user_id},friend_id.eq.{friend_id}),and(user_id.eq.{friend_id},friend_id.eq.{user_id})")
        .maybe_single()
        .execute()
    )
    if existing and existing.data:
        raise HTTPException(status_code=400, detail="Ya existe una relación o solicitud con este usuario")

    ins = supabase_admin.table("friendships").insert({
        "user_id": user_id,
        "friend_id": friend_id,
        "status": "pending"
    }).execute()

    return {"success": True, "message": "Solicitud de amistad enviada"}


@router.post("/friends/respond")
def respond_friend(body: RespondFriendRequest, user_id: str = Depends(get_current_user)):
    f_res = supabase_admin.table("friendships").select("*").eq("id", body.friendship_id).maybe_single().execute()
    if not f_res or not f_res.data:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    friendship = f_res.data
    if friendship["friend_id"] != user_id:
        raise HTTPException(status_code=403, detail="No autorizado para responder esta solicitud")

    if body.action == "accept":
        supabase_admin.table("friendships").update({"status": "accepted"}).eq("id", body.friendship_id).execute()
        return {"success": True, "message": "Amistad aceptada"}
    else:
        supabase_admin.table("friendships").delete().eq("id", body.friendship_id).execute()
        return {"success": True, "message": "Solicitud rechazada"}


@router.post("/groups")
def create_group(body: CreateGroupRequest, user_id: str = Depends(get_current_user)):
    # Participants: creator + selected friends (minimum 2 total)
    participants = list(set([user_id] + body.friend_ids))
    if len(participants) < 2:
        raise HTTPException(status_code=400, detail="Se requiere al menos un amigo para crear el grupo (mínimo 2 participantes)")

    # Verify that user is friends with all selected friend_ids
    for fid in body.friend_ids:
        if fid == user_id:
            continue
        f_check = (
            supabase_admin.table("friendships")
            .select("status")
            .eq("status", "accepted")
            .or_(f"and(user_id.eq.{user_id},friend_id.eq.{fid}),and(user_id.eq.{fid},friend_id.eq.{user_id})")
            .maybe_single()
            .execute()
        )
        if not f_check or not f_check.data:
            raise HTTPException(status_code=400, detail=f"El usuario {fid} no es tu amigo aceptado")

    # Create group
    g_res = supabase_admin.table("groups").insert({
        "name": body.name.strip(),
        "creator_id": user_id
    }).execute()

    if not g_res or not g_res.data:
        raise HTTPException(status_code=500, detail="Error al crear el grupo")

    group_id = g_res.data[0]["id"]

    # Insert members
    members_payload = [{"group_id": group_id, "user_id": pid, "status": "active"} for pid in participants]
    supabase_admin.table("group_members").insert(members_payload).execute()

    return {"success": True, "group_id": group_id}


@router.get("/groups")
def get_user_groups(user_id: str = Depends(get_current_user)):
    # Find groups where user is a member
    gm_res = supabase_admin.table("group_members").select("group_id").eq("user_id", user_id).execute()
    if not gm_res or not gm_res.data:
        return {"groups": []}

    group_ids = [row["group_id"] for row in gm_res.data]
    g_res = supabase_admin.table("groups").select("*").in_("id", group_ids).order("created_at", desc=True).execute()
    if not g_res or not g_res.data:
        return {"groups": []}

    groups = g_res.data
    today = date.today()

    formatted_groups = []
    for g in groups:
        g_id = g["id"]
        created_at_dt = datetime.fromisoformat(g["created_at"].replace("Z", "+00:00"))
        start_date = created_at_dt.date()

        # Get all members of this group
        m_res = supabase_admin.table("group_members").select("user_id, status, eliminated_at, created_at").eq("group_id", g_id).execute()
        members = m_res.data if m_res and m_res.data else []

        user_ids = [m["user_id"] for m in members]
        p_res = supabase_admin.table("profiles").select("id, username, friend_code").in_("id", user_ids).execute()
        profiles_map = {p["id"]: p for p in (p_res.data if p_res and p_res.data else [])}

        # Check challenge completions for each member from start_date to yesterday
        # Rule: if any past day between start_date and yesterday has 0 completed challenges, member is eliminated.
        yesterday = today - timedelta(days=1)
        
        updated_members = []
        for m in members:
            m_uid = m["user_id"]
            m_status = m["status"]
            
            if m_status == "active" and start_date <= yesterday:
                # Query completed challenges for this user from start_date to yesterday
                c_res = (
                    supabase_admin.table("daily_challenges")
                    .select("challenge_date, is_completed")
                    .eq("user_id", m_uid)
                    .eq("is_completed", True)
                    .gte("challenge_date", start_date.isoformat())
                    .lte("challenge_date", yesterday.isoformat())
                    .execute()
                )
                completed_dates = set(row["challenge_date"] for row in (c_res.data if c_res and c_res.data else []))

                # Check every single day from start_date to yesterday
                current_d = start_date
                missed = False
                while current_d <= yesterday:
                    if current_d.isoformat() not in completed_dates:
                        missed = True
                        break
                    current_d += timedelta(days=1)

                if missed:
                    m_status = "eliminated"
                    # Update in DB
                    supabase_admin.table("group_members").update({
                        "status": "eliminated",
                        "eliminated_at": datetime.now().isoformat()
                    }).eq("group_id", g_id).eq("user_id", m_uid).execute()

            profile = profiles_map.get(m_uid, {"id": m_uid, "username": "Usuario", "friend_code": ""})
            updated_members.append({
                "user_id": m_uid,
                "username": profile.get("username"),
                "friend_code": profile.get("friend_code"),
                "status": m_status,
                "is_creator": m_uid == g["creator_id"]
            })

        active_count = sum(1 for m in updated_members if m["status"] == "active")
        winner = updated_members[0] if len(updated_members) == 1 and updated_members[0]["status"] == "active" else None
        if active_count == 1:
            winner = next(m for m in updated_members if m["status"] == "active")

        formatted_groups.append({
            "id": g_id,
            "name": g["name"],
            "creator_id": g["creator_id"],
            "created_at": g["created_at"],
            "start_date": start_date.isoformat(),
            "members": updated_members,
            "active_count": active_count,
            "winner": winner
        })

    return {"groups": formatted_groups}


@router.delete("/groups/{group_id}")
def delete_group(group_id: str, user_id: str = Depends(get_current_user)):
    g_res = supabase_admin.table("groups").select("creator_id").eq("id", group_id).maybe_single().execute()
    if not g_res or not g_res.data:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    
    if g_res.data["creator_id"] != user_id:
        raise HTTPException(status_code=403, detail="Solo el creador puede eliminar el grupo")

    supabase_admin.table("groups").delete().eq("id", group_id).execute()
    return {"success": True}
