import uvicorn

if __name__ == "__main__":
    uvicorn.run("monitorr_ii.app:app", host="0.0.0.0", port=8000, proxy_headers=True)
