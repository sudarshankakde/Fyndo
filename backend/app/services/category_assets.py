"""
Category Assets Service:
- Default cover images and profile logos for all 20 store types.
- WebP conversion and bucket/local storage utilities.
"""
import io
import os
import uuid
from typing import Optional
from PIL import Image

from app.core.config import settings
from app.services.cloudinary_service import CloudinaryService

# Normalized mappings for backward compatibility
SECTOR_NORMALIZE = {
    "FOOD": "RESTAURANTS_DINING",
    "FASHION": "FASHION_CLOTHING",
    "FOOTWEAR": "FASHION_CLOTHING",
}

VALID_SECTORS = {
    "FASHION_CLOTHING",
    "GROCERY_SUPERMARKET",
    "CAFE_COFFEE_SHOPS",
    "ELECTRONICS",
    "BEAUTY_PERSONAL_CARE",
    "HOME_LIVING",
    "SPORTS_FITNESS",
    "BOOKS_STATIONERY",
    "KIDS_TOYS",
    "REAL_ESTATE",
    "JEWELRY_ACCESSORIES",
    "TRAVEL_LUGGAGE",
    "FAST_FOOD",
    "RESTAURANTS_DINING",
    "SALON_SPA",
    "ENTERTAINMENT",
    "SPORTS_ACTIVITY_CENTERS",
    "PETS_SUPPLIES",
    "EVENTS_FESTIVALS",
    "OTHER",
}

STORE_CATEGORIES_METADATA = [
    {
        "id": "FASHION_CLOTHING",
        "name": "Fashion & Clothing",
        "icon": "Shirt",
        "sub_categories": ["Men's Wear", "Women's Wear", "Ethnic & Traditional", "Western Wear", "Footwear & Shoes", "Watches & Accessories", "Kids Wear"],
    },
    {
        "id": "GROCERY_SUPERMARKET",
        "name": "Grocery & Supermarket",
        "icon": "ShoppingBag",
        "sub_categories": ["Fresh Fruits & Veggies", "Dairy & Eggs", "Daily Staples & Spices", "Beverages & Soft Drinks", "Packaged Snacks", "Organic & Gourmet", "Household Essentials"],
    },
    {
        "id": "CAFE_COFFEE_SHOPS",
        "name": "Café & Coffee Shops",
        "icon": "Coffee",
        "sub_categories": ["Artisanal Coffee", "Espresso & Brews", "Bakery & Pastries", "Breakfast & Brunch", "Desserts & Cakes", "Teas & Shakes", "Free WiFi & Workspaces"],
    },
    {
        "id": "ELECTRONICS",
        "name": "Electronics & Gadgets",
        "icon": "Smartphone",
        "sub_categories": ["Smartphones & Accessories", "Laptops & Computers", "Audio & Headphones", "Home & Kitchen Appliances", "Smartwatches", "Device Repairs"],
    },
    {
        "id": "BEAUTY_PERSONAL_CARE",
        "name": "Beauty & Personal Care",
        "icon": "Sparkles",
        "sub_categories": ["Skincare & Serums", "Hair Care & Styling", "Makeup & Cosmetics", "Fragrances & Perfumes", "Organic & Herbal", "Personal Hygiene"],
    },
    {
        "id": "HOME_LIVING",
        "name": "Home & Living",
        "icon": "Home",
        "sub_categories": ["Furniture & Sofas", "Home Decor & Wall Art", "Kitchen & Dining Ware", "Bedding & Cushions", "Curtains & Rugs", "Indoor Plants & Garden"],
    },
    {
        "id": "SPORTS_FITNESS",
        "name": "Sports & Fitness",
        "icon": "Dumbbell",
        "sub_categories": ["Gym & Crossfit", "Activewear & Shoes", "Protein & Supplements", "Sports Equipment", "Yoga & Pilates", "Bicycles & Accessories"],
    },
    {
        "id": "BOOKS_STATIONERY",
        "name": "Books & Stationery",
        "icon": "BookOpen",
        "sub_categories": ["Novels & Fiction", "Academic & College Books", "Stationery & Journals", "Art & Craft Supplies", "Office Supplies", "Manga & Comics"],
    },
    {
        "id": "KIDS_TOYS",
        "name": "Kids & Toys",
        "icon": "Smile",
        "sub_categories": ["Educational & STEM Toys", "Board Games & Puzzles", "Action Figures & Dolls", "Baby & Infant Care", "Ride-on Toys & Cycles"],
    },
    {
        "id": "REAL_ESTATE",
        "name": "Real Estate",
        "icon": "Building",
        "sub_categories": ["Residential Flats", "Independent Houses & Villas", "Commercial Offices", "Plots & Land", "Rental Properties"],
    },
    {
        "id": "JEWELRY_ACCESSORIES",
        "name": "Jewelry & Accessories",
        "icon": "Gem",
        "sub_categories": ["Gold & Diamond", "Silver Jewelry", "Fashion & Imitation", "Handbags & Clutches", "Sunglasses & Belts"],
    },
    {
        "id": "TRAVEL_LUGGAGE",
        "name": "Travel & Luggage",
        "icon": "Luggage",
        "sub_categories": ["Trolley Bags & Suitcases", "Backpacks & Rucksacks", "Travel Accessories", "Duffel & Gym Bags"],
    },
    {
        "id": "FAST_FOOD",
        "name": "Fast Food & Quick Bites",
        "icon": "UtensilsCrossed",
        "sub_categories": ["Burgers & Wraps", "Pizza & Pasta", "Street Food & Chaat", "Rolls & Shawarma", "Crispy Fries", "Shakes & Beverages"],
    },
    {
        "id": "RESTAURANTS_DINING",
        "name": "Restaurants & Dining",
        "icon": "Utensils",
        "sub_categories": ["North Indian", "South Indian", "Mughlai & Biryani", "Chinese & Asian", "Italian & Continental", "Fine Dining", "Thali & Meals"],
    },
    {
        "id": "SALON_SPA",
        "name": "Salon & Spa",
        "icon": "Scissors",
        "sub_categories": ["Haircut & Styling", "Beard & Grooming", "Facials & Cleanup", "Hair Spa & Keratin", "Pedicure & Manicure", "Bridal & Party Makeup", "Relaxing Massage"],
    },
    {
        "id": "ENTERTAINMENT",
        "name": "Entertainment & Gaming",
        "icon": "Film",
        "sub_categories": ["Multiplex & Cinema", "Gaming Zone & Arcades", "VR & Simulation", "Live Music & Comedy", "Escape Rooms & Laser Tag"],
    },
    {
        "id": "SPORTS_ACTIVITY_CENTERS",
        "name": "Sports Turfs & Centers",
        "icon": "Trophy",
        "sub_categories": ["Box Cricket Turf", "Football Turf", "Badminton Court", "Swimming Pool", "Snooker & Pool", "Bowling Alley"],
    },
    {
        "id": "PETS_SUPPLIES",
        "name": "Pets & Pet Supplies",
        "icon": "Heart",
        "sub_categories": ["Dog Food & Treats", "Cat Food & Litter", "Pet Grooming & Toys", "Collars, Leashes & Beds", "Vet & Pet Healthcare"],
    },
    {
        "id": "EVENTS_FESTIVALS",
        "name": "Events & Celebrations",
        "icon": "PartyPopper",
        "sub_categories": ["Event Management", "Decoration & Florals", "Sound & Stage Lighting", "Catering Services", "Party Rentals & DJ"],
    },
    {
        "id": "OTHER",
        "name": "Other Local Services",
        "icon": "Tag",
        "sub_categories": ["General Store", "Hardware & Tools", "Tailoring & Alterations", "Dry Cleaning & Laundry", "Printing & Xerox", "Specialty Services"],
    },
]


def normalize_sector(sector: Optional[str]) -> str:
    """Normalizes raw sector string into standard Store Type enum key."""
    if not sector:
        return "OTHER"
    upper = sector.strip().upper()
    mapped = SECTOR_NORMALIZE.get(upper, upper)
    if mapped in VALID_SECTORS:
        return mapped
    return "OTHER"


def get_default_cover_url(sector: Optional[str]) -> str:
    """Returns the default background cover URL for the shop category."""
    norm = normalize_sector(sector)
    filename = f"{norm.lower()}.webp"
    return f"/uploads/covers/{filename}"


def get_default_logo_url(sector: Optional[str]) -> str:
    """Returns the default circular profile logo URL for the shop type."""
    norm = normalize_sector(sector)
    filename = f"{norm.lower()}.webp"
    return f"/uploads/logos/{filename}"


def convert_to_webp(
    image_bytes: bytes,
    max_dimension: int = 1920,
    quality: int = 85
) -> bytes:
    """
    Converts raw image bytes to highly optimized WebP format.
    Automatically scales down images exceeding max_dimension.
    """
    with Image.open(io.BytesIO(image_bytes)) as img:
        # Preserve transparency for RGBA, or convert to RGB
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            processed = img.convert("RGBA")
        else:
            processed = img.convert("RGB")

        # Scale down if exceeds max_dimension
        w, h = processed.size
        if max(w, h) > max_dimension:
            scale = max_dimension / float(max(w, h))
            new_size = (int(w * scale), int(h * scale))
            processed = processed.resize(new_size, Image.Resampling.LANCZOS)

        out_io = io.BytesIO()
        processed.save(out_io, format="WEBP", quality=quality, method=6)
        return out_io.getvalue()


async def save_image_to_bucket(
    image_bytes: bytes,
    folder: str = "covers",
    custom_filename: Optional[str] = None,
    quality: int = 85
) -> str:
    """
    Converts image to WebP, then stores in Cloudinary or local bucket directory.
    Returns the public URL (Cloudinary CDN URL or /uploads/<folder>/<filename>).
    """
    webp_bytes = convert_to_webp(image_bytes, quality=quality)
    filename = custom_filename or f"{uuid.uuid4().hex}.webp"
    if not filename.endswith(".webp"):
        filename = f"{os.path.splitext(filename)[0]}.webp"

    # Save to local uploads bucket directory
    upload_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../uploads", folder))
    os.makedirs(upload_root, exist_ok=True)
    local_path = os.path.join(upload_root, filename)
    with open(local_path, "wb") as f:
        f.write(webp_bytes)

    # If Cloudinary is configured, upload to Cloudinary bucket
    if settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET:
        try:
            cloud_res = CloudinaryService.upload_file(local_path, folder=folder, resource_type="image")
            if cloud_res and cloud_res.get("url"):
                return cloud_res["url"]
        except Exception:
            pass

    return f"/uploads/{folder}/{filename}"
