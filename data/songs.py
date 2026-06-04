"""
Sample music dataset for the recommendation system.

Each song has:
  id, title, artist, album, language, genre, year, duration, color
The `color` is a hex used to render a unique gradient album cover in the UI
(so we don't need network access for images).

`similar_artists` maps an artist to a list of artists considered similar
(used by the "smart" recommendation fallback when same-artist songs run out).
"""

SONGS = [
    # ---------------- Darshan Raval ----------------
    {"id": 1,  "title": "Tera Zikr",        "artist": "Darshan Raval", "album": "Tera Zikr",         "language": "Hindi",    "genre": "Romantic", "year": 2018, "duration": "3:55", "color": "#7c3aed"},
    {"id": 2,  "title": "Hawa Banke",       "artist": "Darshan Raval", "album": "Judaiyaan",         "language": "Hindi",    "genre": "Romantic", "year": 2019, "duration": "3:45", "color": "#a855f7"},
    {"id": 3,  "title": "Ek Tarfa",         "artist": "Darshan Raval", "album": "The Unplugged Vol.1","language": "Hindi",    "genre": "Romantic", "year": 2020, "duration": "3:32", "color": "#9333ea"},
    {"id": 4,  "title": "Baarish",          "artist": "Darshan Raval", "album": "Judaiyaan",         "language": "Hindi",    "genre": "Romantic", "year": 2019, "duration": "3:14", "color": "#6d28d9"},
    {"id": 5,  "title": "Kaash Aisa Hota",  "artist": "Darshan Raval", "album": "Kaash Aisa Hota",   "language": "Hindi",    "genre": "Sad",      "year": 2019, "duration": "3:41", "color": "#5b21b6"},
    {"id": 6,  "title": "Asal Mein",        "artist": "Darshan Raval", "album": "Asal Mein",         "language": "Hindi",    "genre": "Romantic", "year": 2020, "duration": "3:29", "color": "#8b5cf6"},
    {"id": 7,  "title": "Naseeb Se",        "artist": "Darshan Raval", "album": "Naseeb Se",         "language": "Hindi",    "genre": "Romantic", "year": 2021, "duration": "3:18", "color": "#7e22ce"},
    {"id": 8,  "title": "Chogada",          "artist": "Darshan Raval", "album": "Loveyatri",         "language": "Hindi",    "genre": "Dance",    "year": 2018, "duration": "3:13", "color": "#a21caf"},
    {"id": 9,  "title": "Kamariya",         "artist": "Darshan Raval", "album": "Mitron",            "language": "Hindi",    "genre": "Dance",    "year": 2018, "duration": "3:10", "color": "#c026d3"},

    # ---------------- Arijit Singh ----------------
    {"id": 10, "title": "Tum Hi Ho",            "artist": "Arijit Singh", "album": "Aashiqui 2",     "language": "Hindi",    "genre": "Romantic", "year": 2013, "duration": "4:22", "color": "#0ea5e9"},
    {"id": 11, "title": "Channa Mereya",        "artist": "Arijit Singh", "album": "Ae Dil Hai Mushkil","language": "Hindi", "genre": "Sad",      "year": 2016, "duration": "4:49", "color": "#0284c7"},
    {"id": 12, "title": "Kesariya",             "artist": "Arijit Singh", "album": "Brahmastra",     "language": "Hindi",    "genre": "Romantic", "year": 2022, "duration": "4:28", "color": "#f59e0b"},
    {"id": 13, "title": "Kabira",               "artist": "Arijit Singh", "album": "Yeh Jawaani Hai Deewani","language":"Hindi","genre":"Romantic","year": 2013, "duration": "3:43", "color": "#0369a1"},
    {"id": 14, "title": "Raabta",               "artist": "Arijit Singh", "album": "Agent Vinod",    "language": "Hindi",    "genre": "Romantic", "year": 2012, "duration": "4:24", "color": "#075985"},
    {"id": 15, "title": "Apna Bana Le",         "artist": "Arijit Singh", "album": "Bhediya",        "language": "Hindi",    "genre": "Romantic", "year": 2022, "duration": "4:11", "color": "#0c4a6e"},
    {"id": 16, "title": "Phir Bhi Tumko Chaahunga","artist":"Arijit Singh","album": "Half Girlfriend","language": "Hindi",   "genre": "Sad",      "year": 2017, "duration": "4:45", "color": "#1e40af"},
    {"id": 17, "title": "Agar Tum Saath Ho",    "artist": "Arijit Singh", "album": "Tamasha",        "language": "Hindi",    "genre": "Sad",      "year": 2015, "duration": "5:41", "color": "#1e3a8a"},

    # ---------------- Atif Aslam ----------------
    {"id": 18, "title": "Tera Hone Laga Hoon",  "artist": "Atif Aslam",  "album": "Ajab Prem Ki Ghazab Kahani","language": "Hindi","genre":"Romantic","year": 2009, "duration": "4:43", "color": "#dc2626"},
    {"id": 19, "title": "Tu Jaane Na",          "artist": "Atif Aslam",  "album": "Ajab Prem Ki Ghazab Kahani","language": "Hindi","genre":"Sad",     "year": 2009, "duration": "5:15", "color": "#b91c1c"},
    {"id": 20, "title": "Jeena Jeena",          "artist": "Atif Aslam",  "album": "Badlapur",       "language": "Hindi",    "genre": "Romantic", "year": 2015, "duration": "3:49", "color": "#991b1b"},
    {"id": 21, "title": "Pehli Nazar Mein",     "artist": "Atif Aslam",  "album": "Race",           "language": "Hindi",    "genre": "Romantic", "year": 2008, "duration": "5:18", "color": "#ef4444"},
    {"id": 22, "title": "Tere Sang Yaara",      "artist": "Atif Aslam",  "album": "Rustom",         "language": "Hindi",    "genre": "Romantic", "year": 2016, "duration": "4:08", "color": "#7f1d1d"},
    {"id": 23, "title": "Dil Diyan Gallan",     "artist": "Atif Aslam",  "album": "Tiger Zinda Hai","language": "Hindi",    "genre": "Romantic", "year": 2017, "duration": "4:37", "color": "#f87171"},

    # ---------------- Jubin Nautiyal ----------------
    {"id": 24, "title": "Lut Gaye",             "artist": "Jubin Nautiyal","album": "Lut Gaye",      "language": "Hindi",    "genre": "Sad",      "year": 2021, "duration": "4:02", "color": "#10b981"},
    {"id": 25, "title": "Raataan Lambiyan",     "artist": "Jubin Nautiyal","album": "Shershaah",     "language": "Hindi",    "genre": "Romantic", "year": 2021, "duration": "3:50", "color": "#059669"},
    {"id": 26, "title": "Tum Hi Aana",          "artist": "Jubin Nautiyal","album": "Marjaavaan",    "language": "Hindi",    "genre": "Sad",      "year": 2019, "duration": "5:21", "color": "#047857"},
    {"id": 27, "title": "Meri Aashiqui",        "artist": "Jubin Nautiyal","album": "Meri Aashiqui", "language": "Hindi",    "genre": "Romantic", "year": 2021, "duration": "4:42", "color": "#065f46"},
    {"id": 28, "title": "Dil Galti Kar Baitha", "artist": "Jubin Nautiyal","album": "Dil Galti Kar Baitha","language": "Hindi","genre": "Sad",     "year": 2020, "duration": "4:58", "color": "#34d399"},

    # ---------------- Armaan Malik ----------------
    {"id": 29, "title": "Bol Do Na Zara",       "artist": "Armaan Malik", "album": "Azhar",         "language": "Hindi",    "genre": "Romantic", "year": 2016, "duration": "4:17", "color": "#f97316"},
    {"id": 30, "title": "Wajah Tum Ho",         "artist": "Armaan Malik", "album": "Hate Story 3",  "language": "Hindi",    "genre": "Romantic", "year": 2015, "duration": "4:42", "color": "#ea580c"},
    {"id": 31, "title": "Pehla Pyaar",          "artist": "Armaan Malik", "album": "Kabir Singh",   "language": "Hindi",    "genre": "Romantic", "year": 2019, "duration": "3:28", "color": "#c2410c"},
    {"id": 32, "title": "Butta Bomma",          "artist": "Armaan Malik", "album": "Ala Vaikunthapurramuloo","language":"Telugu","genre":"Dance","year":2020, "duration": "3:36", "color": "#fb923c"},
    {"id": 33, "title": "Tujhe Kitna Chahne Lage","artist":"Armaan Malik","album": "Kabir Singh",   "language": "Hindi",    "genre": "Romantic", "year": 2019, "duration": "4:48", "color": "#9a3412"},

    # ---------------- B Praak ----------------
    {"id": 34, "title": "Filhall",              "artist": "B Praak",     "album": "Filhall",        "language": "Hindi",    "genre": "Sad",      "year": 2019, "duration": "4:41", "color": "#facc15"},
    {"id": 35, "title": "Mann Bharrya",         "artist": "B Praak",     "album": "Mann Bharrya",   "language": "Punjabi",  "genre": "Sad",      "year": 2017, "duration": "5:03", "color": "#eab308"},
    {"id": 36, "title": "Dil Tod Ke",           "artist": "B Praak",     "album": "Dil Tod Ke",     "language": "Hindi",    "genre": "Sad",      "year": 2020, "duration": "4:14", "color": "#ca8a04"},
    {"id": 37, "title": "Pachtaoge",            "artist": "B Praak",     "album": "Pachtaoge",      "language": "Hindi",    "genre": "Sad",      "year": 2019, "duration": "4:11", "color": "#a16207"},
    {"id": 38, "title": "Qismat",               "artist": "B Praak",     "album": "Qismat",         "language": "Punjabi",  "genre": "Sad",      "year": 2018, "duration": "4:32", "color": "#fde047"},

    # ---------------- Neha Kakkar ----------------
    {"id": 39, "title": "Dilbar",               "artist": "Neha Kakkar", "album": "Satyameva Jayate","language": "Hindi",   "genre": "Dance",    "year": 2018, "duration": "3:13", "color": "#ec4899"},
    {"id": 40, "title": "Mile Ho Tum",          "artist": "Neha Kakkar", "album": "Fever",          "language": "Hindi",    "genre": "Romantic", "year": 2016, "duration": "3:27", "color": "#db2777"},
    {"id": 41, "title": "Kala Chashma",         "artist": "Neha Kakkar", "album": "Baar Baar Dekho","language": "Hindi",    "genre": "Dance",    "year": 2016, "duration": "3:46", "color": "#be185d"},
    {"id": 42, "title": "Coca Cola",            "artist": "Neha Kakkar", "album": "Luka Chuppi",    "language": "Hindi",    "genre": "Dance",    "year": 2019, "duration": "3:00", "color": "#9d174d"},

    # ---------------- Ed Sheeran ----------------
    {"id": 43, "title": "Shape of You",         "artist": "Ed Sheeran",  "album": "Divide",         "language": "English",  "genre": "Pop",      "year": 2017, "duration": "3:53", "color": "#22c55e"},
    {"id": 44, "title": "Perfect",              "artist": "Ed Sheeran",  "album": "Divide",         "language": "English",  "genre": "Romantic", "year": 2017, "duration": "4:23", "color": "#16a34a"},
    {"id": 45, "title": "Photograph",           "artist": "Ed Sheeran",  "album": "x",              "language": "English",  "genre": "Romantic", "year": 2014, "duration": "4:18", "color": "#15803d"},
    {"id": 46, "title": "Thinking Out Loud",    "artist": "Ed Sheeran",  "album": "x",              "language": "English",  "genre": "Romantic", "year": 2014, "duration": "4:41", "color": "#166534"},
    {"id": 47, "title": "Bad Habits",           "artist": "Ed Sheeran",  "album": "Equals",         "language": "English",  "genre": "Pop",      "year": 2021, "duration": "3:51", "color": "#4ade80"},

    # ---------------- Taylor Swift ----------------
    {"id": 48, "title": "Blank Space",          "artist": "Taylor Swift","album": "1989",            "language": "English", "genre": "Pop",      "year": 2014, "duration": "3:51", "color": "#f43f5e"},
    {"id": 49, "title": "Shake It Off",         "artist": "Taylor Swift","album": "1989",            "language": "English", "genre": "Pop",      "year": 2014, "duration": "3:39", "color": "#e11d48"},
    {"id": 50, "title": "Love Story",           "artist": "Taylor Swift","album": "Fearless",        "language": "English", "genre": "Romantic", "year": 2008, "duration": "3:55", "color": "#be123c"},
    {"id": 51, "title": "Anti-Hero",            "artist": "Taylor Swift","album": "Midnights",       "language": "English", "genre": "Pop",      "year": 2022, "duration": "3:20", "color": "#9f1239"},
    {"id": 52, "title": "Cardigan",             "artist": "Taylor Swift","album": "Folklore",        "language": "English", "genre": "Pop",      "year": 2020, "duration": "3:59", "color": "#fb7185"},

    # ---------------- The Weeknd ----------------
    {"id": 53, "title": "Blinding Lights",      "artist": "The Weeknd",  "album": "After Hours",     "language": "English", "genre": "Pop",      "year": 2019, "duration": "3:20", "color": "#64748b"},
    {"id": 54, "title": "Starboy",              "artist": "The Weeknd",  "album": "Starboy",         "language": "English", "genre": "Pop",      "year": 2016, "duration": "3:50", "color": "#475569"},
    {"id": 55, "title": "Save Your Tears",      "artist": "The Weeknd",  "album": "After Hours",     "language": "English", "genre": "Pop",      "year": 2020, "duration": "3:35", "color": "#334155"},
    {"id": 56, "title": "Die For You",          "artist": "The Weeknd",  "album": "Starboy",         "language": "English", "genre": "Romantic", "year": 2016, "duration": "4:20", "color": "#1e293b"},
]


# Map of artist -> list of similar artists. Used by the "smart" fallback
# recommendation when the same-artist pool is exhausted.
SIMILAR_ARTISTS = {
    "Darshan Raval":   ["Jubin Nautiyal", "Armaan Malik", "Atif Aslam", "Arijit Singh"],
    "Arijit Singh":    ["Atif Aslam", "Jubin Nautiyal", "Armaan Malik", "Darshan Raval"],
    "Atif Aslam":      ["Arijit Singh", "Darshan Raval", "Armaan Malik", "Jubin Nautiyal"],
    "Jubin Nautiyal":  ["Darshan Raval", "Arijit Singh", "B Praak", "Armaan Malik"],
    "Armaan Malik":    ["Darshan Raval", "Arijit Singh", "Atif Aslam", "Jubin Nautiyal"],
    "B Praak":         ["Jubin Nautiyal", "Arijit Singh", "Atif Aslam"],
    "Neha Kakkar":     ["Armaan Malik", "Darshan Raval", "Jubin Nautiyal"],
    "Ed Sheeran":      ["Taylor Swift", "The Weeknd"],
    "Taylor Swift":    ["Ed Sheeran", "The Weeknd"],
    "The Weeknd":      ["Ed Sheeran", "Taylor Swift"],
}
