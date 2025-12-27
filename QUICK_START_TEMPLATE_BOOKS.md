# Quick Start: Template Books

## 🚀 Ready to Use in 3 Steps

### Step 1: Run the App
```bash
streamlit run main.py
```

### Step 2: Select Template Book Mode
- Look at the top of the page
- Click on **"Template Book"** (radio button)

### Step 3: Fill the Form
- **Child's Name**: Emma, Alex, etc.
- **Age**: 2-16 years
- **Gender**: Boy/Girl/Non-binary
- **Upload 3 Photos**: Clear face photos

Click **"Generate My Personalized Book"**

## 📖 What You Get

A 24-page personalized book with:
- Astronaut, Doctor, Teacher, Firefighter, Chef, Pilot
- Veterinarian, Army Officer, Wildlife Conservationist
- Martial Artist, Detective, Magician, Artist, Musician
- Scientist, Engineer, Athlete, Marine Biologist
- Fashion Designer, Architect, Photographer
- Business Leader, Writer, Dreamer

## 💡 Key Points

✅ **No API key needed** for text preview
✅ **Database works everywhere** (Cursor, Bolt, local)
✅ **Already populated** with 24 professions
✅ **Preview immediately** - see all pages with personalized text
✅ **Add photos** - used for AI image generation later

## 📊 Database Status

**Database**: Supabase (cloud PostgreSQL)
**Status**: ✅ Connected and populated
**Templates**: 1 ("When {name} Grows Up")
**Pages**: 24 profession pages
**Location**: Cloud (accessible everywhere)

## 🔧 Works In All Environments

- ✅ Cursor IDE
- ✅ Bolt.new
- ✅ Local machine
- ✅ Any hosting platform

Same database credentials work everywhere!

## 📝 Example Output

**Input**: Name: Emma, Gender: Girl, Age: 5

**Output (Page 1 - Astronaut)**:
```
When Emma grows up,
she just might be,
an astronaut floating free.
Among the stars and planets bright,
exploring space both day and night!
```

**Output (Page 12 - Magician)**:
```
When Emma grows up,
she just might be,
a wizard of great mystery.
Pulling rabbits, cards that fly,
with a wand held proudly to the sky!
```

## 🎯 Next Steps After Preview

1. Review all 24 pages using the slider
2. Click "Generate Images & PDF" (requires API key)
3. AI creates images showing the child in each profession
4. Download PDF for printing

## 📚 More Info

- **Detailed Guide**: See `TEMPLATE_BOOKS_GUIDE.md`
- **Database Info**: See `DATABASE_SETUP.md`
- **Full Setup**: See `SETUP_SUMMARY.md`

## ⚠️ Troubleshooting

**Can't see preview?**
- Make sure you selected "Template Book" mode at the top
- Click "Generate My Personalized Book" after filling the form

**Database error?**
- Check `.env` file has Supabase credentials
- Credentials are already configured - should work

**Need to add more templates?**
- Edit `template_data.py`
- Run `python seed_template_data.py`
- New templates appear automatically

---

**That's it! You're ready to create personalized books. 🎉**
