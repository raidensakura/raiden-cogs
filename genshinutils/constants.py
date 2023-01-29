"""
Mapping for character names
Key name always need to be properly capitalized and match in-game character name
String on first index always need to match formal name but in all lowercase
This make sure the profile command accepts a variation of valid character names

Ideally I'll want to sort these by character release date
"""
common_names = {
    "Kamisato Ayato": ["kamisato ayato", "ayato"],
    "Kamisato Ayaka": ["kamisato ayaka", "ayaka", "ayaya"],
    "Raiden Shogun": ["raiden shogun", "raiden", "shogun", "ei", "beelzebul"],
    "Arataki Itto": ["arataki itto", "itto", "arataki"],
    # ...
}

"""
Mapping for character namecards
Key name always need to be properly capitalized and match in-game character name
URLs should always belong to enka.network
This make sure commands interfacing with a featured character icon always show their namecard
"""
character_namecards = {
    "Raiden Shogun": "https://enka.network/ui/UI_NameCardPic_Shougun_P.png",
    # ...
}
