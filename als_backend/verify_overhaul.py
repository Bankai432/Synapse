import asyncio
from simulate_student import run_simulation
from datetime import datetime
import os

async def main():
    role = "struggling"
    log_filename = "verify_overhaul_log.txt"
    log_path = os.path.join(os.path.dirname(__file__), log_filename)
    
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"Verification Run started at {datetime.now().isoformat()}\n")
        await run_simulation(role, 8, f) # 8 interactions to ensure we see transitions
        
    print(f"\nVerification complete. Results at {log_path}")

if __name__ == "__main__":
    asyncio.run(main())
