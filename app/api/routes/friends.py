from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from app.db.session import get_db
from app.models.friendship import Friendship, FriendshipStatus
from app.models.user import User
from app.schemas.user import UserResponse
from app.schemas.friendship import FriendshipResponse, FriendshipCreate, FriendListResponse, PendingRequestResponse
from app.schemas.common import APIResponse
from app.core.dependencies import get_current_user
from app.services.notification_service import notification_service
from typing import List
from uuid import UUID

router = APIRouter()

@router.post("/request/{friend_id}", response_model=APIResponse[FriendshipResponse])
async def send_friend_request(
    friend_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if friend_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot send a friend request to yourself")

    # Check if user exists
    friend = await db.get(User, friend_id)
    if not friend:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if request already exists
    query = select(Friendship).where(
        or_(
            and_(Friendship.user_id == current_user.id, Friendship.friend_id == friend_id),
            and_(Friendship.user_id == friend_id, Friendship.friend_id == current_user.id)
        )
    )
    result = await db.execute(query)
    existing = result.scalars().first()

    if existing:
        if existing.status == FriendshipStatus.ACCEPTED:
            raise HTTPException(status_code=400, detail="You are already friends")
        if existing.status == FriendshipStatus.PENDING:
            if existing.user_id == current_user.id:
                raise HTTPException(status_code=400, detail="Request already sent")
            else:
                # Other person already sent a request, so just accept it
                existing.status = FriendshipStatus.ACCEPTED
                await db.commit()
                return APIResponse(status=True, message="Friend request accepted", data=existing)

    new_request = Friendship(user_id=current_user.id, friend_id=friend_id)
    db.add(new_request)
    await db.commit()
    await db.refresh(new_request)

    # Send Notification
    if friend.fcm_token:
        await notification_service.send_push_notification(
            token=friend.fcm_token,
            title="New Friend Request",
            body=f"{current_user.username} sent you a friend request",
            data={"type": "friend_request", "sender_id": str(current_user.id)}
        )

    return APIResponse(status=True, message="Friend request sent", data=new_request)

@router.get("/pending", response_model=APIResponse[List[PendingRequestResponse]])
async def get_pending_requests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Only show requests where current_user is the receiver (friend_id)
    query = select(Friendship, User).join(User, User.id == Friendship.user_id).where(
        and_(Friendship.friend_id == current_user.id, Friendship.status == FriendshipStatus.PENDING)
    )
    result = await db.execute(query)
    rows = result.all()
    
    pending = [
        PendingRequestResponse(
            id=f.id,
            sender=u,
            created_at=f.created_at
        ) for f, u in rows
    ]
    
    return APIResponse(status=True, message="Pending requests retrieved", data=pending)

@router.get("/outgoing", response_model=APIResponse[List[FriendshipResponse]])
async def get_outgoing_requests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Show requests where current_user is the sender (user_id)
    query = select(Friendship).where(
        and_(Friendship.user_id == current_user.id, Friendship.status == FriendshipStatus.PENDING)
    )
    result = await db.execute(query)
    outgoing = result.scalars().all()
    
    return APIResponse(status=True, message="Outgoing requests retrieved", data=outgoing)

@router.post("/accept/{request_id}", response_model=APIResponse[FriendshipResponse])
async def accept_friend_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    request = await db.get(Friendship, request_id)
    if not request or request.friend_id != current_user.id:
        raise HTTPException(status_code=404, detail="Request not found")

    if request.status != FriendshipStatus.PENDING:
        raise HTTPException(status_code=400, detail="Request already processed")

    request.status = FriendshipStatus.ACCEPTED
    await db.commit()
    await db.refresh(request)

    # Send Notification to the sender
    sender = await db.get(User, request.user_id)
    if sender and sender.fcm_token:
        await notification_service.send_push_notification(
            token=sender.fcm_token,
            title="Friend Request Accepted",
            body=f"{current_user.username} accepted your friend request",
            data={"type": "friend_accepted", "friend_id": str(current_user.id)}
        )

    return APIResponse(status=True, message="Friend request accepted", data=request)

@router.post("/reject/{request_id}", response_model=APIResponse[FriendshipResponse])
async def reject_friend_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    request = await db.get(Friendship, request_id)
    if not request or request.friend_id != current_user.id:
        raise HTTPException(status_code=404, detail="Request not found")

    request.status = FriendshipStatus.REJECTED
    await db.commit()
    
    return APIResponse(status=True, message="Friend request rejected", data=request)

@router.get("/list", response_model=APIResponse[List[UserResponse]])
async def get_friends_list(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get all friendships where status is accepted and current_user is either user_id or friend_id
    query = select(Friendship).where(
        and_(
            or_(Friendship.user_id == current_user.id, Friendship.friend_id == current_user.id),
            Friendship.status == FriendshipStatus.ACCEPTED
        )
    )
    result = await db.execute(query)
    friendships = result.scalars().all()
    
    friend_ids = []
    for f in friendships:
        if f.user_id == current_user.id:
            friend_ids.append(f.friend_id)
        else:
            friend_ids.append(f.user_id)
            
    if not friend_ids:
        return APIResponse(status=True, message="Friends list retrieved", data=[])
        
    query_users = select(User).where(User.id.in_(friend_ids))
    result_users = await db.execute(query_users)
    friends = result_users.scalars().all()
    
    return APIResponse(status=True, message="Friends list retrieved", data=friends)
