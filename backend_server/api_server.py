from fastapi import FastAPI

from routers import auth, admin, pin, work_schedule, tool_logs, task_follow

app = FastAPI()


@app.get("/")
def root():
    return {"status": "API OK"}


@app.on_event("startup")
def bootstrap_app_schema():
    task_follow.bootstrap_task_follow_schema()
    pin.bootstrap_pin_schema()


app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(pin.router)
app.include_router(work_schedule.router)
app.include_router(tool_logs.router)
app.include_router(task_follow.router)
