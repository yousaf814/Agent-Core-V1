import os

from dotenv import load_dotenv
from supabase import create_client, Client


# --------------------------------------------------
# 1. Load environment variables
# --------------------------------------------------

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_secret_key = os.getenv("SUPABASE_SECRET_KEY")

if not supabase_url:
    raise ValueError("SUPABASE_URL is not set in the .env file.")

if not supabase_secret_key:
    raise ValueError(
        "SUPABASE_SECRET_KEY is not set in the .env file."
    )

# --------------------------------------------------
# 2. Create Supabase client
# --------------------------------------------------

supabase: Client = create_client(
    supabase_url,
    supabase_secret_key,
)

# --------------------------------------------------
# 3. Get current lead count
# --------------------------------------------------

def get_lead_count() -> int:
    """
    Return the exact number of leads in the leads table.
    """
    response = (
        supabase.table("leads").select("id", count="exact").execute()
    )
    
    if response.count is None:

        raise RuntimeError("Supabase did not return a lead count.")
    
    return response.count

# --------------------------------------------------
# 4. Local test
# --------------------------------------------------

if __name__ == "__main__":
    count = get_lead_count()
    print(f"Total leads: {count}")
