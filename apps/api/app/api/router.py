from fastapi import APIRouter

from app.api.routes import (
    admin,
    agents,
    analytics,
    auth,
    comments,
    context,
    flow,
    governance,
    health,
    integrations,
    knowledge,
    notifications,
    orgs,
    pilot,
    skills,
    teams,
    users,
    waitlist,
)
from app.api.routes import agent as agent_loop

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(orgs.router, prefix="/orgs", tags=["organizations"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
api_router.include_router(context.router, prefix="/context", tags=["context"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(flow.router, prefix="/flow", tags=["flow"])
api_router.include_router(pilot.router, prefix="/pilot", tags=["pilot"])
api_router.include_router(skills.router, prefix="/skills", tags=["skills"])
api_router.include_router(governance.router, prefix="/governance", tags=["governance"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(waitlist.router, prefix="/waitlist", tags=["waitlist"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(agent_loop.router, prefix="/agent", tags=["agent-loop"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(teams.router, prefix="/teams", tags=["teams"])
api_router.include_router(comments.router, prefix="/comments", tags=["comments"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
