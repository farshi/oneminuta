now we have a lot of features for , i think the most importnat part is having smooth flow for usr experience

users on boariding will be done only form TG for now

we need to add userRoles t to the system 

1-admin 2-partners ( for now property agents late car and bike and s..) typical users 

- admin can add / remove partners by their telegram users

-  partner should have a T.G channel , they post their list wich has a md text( description) and media group .

- we are using llm heavily for MVP and we use prompts for 

1- greetings 2-partner-on-boariding 3-users-on-boaridng 4-parsing text of listings 5-reporting results for usrers 6-reporting analytics for partner channel , 7-reporting analytics for admin 8-help page for partners and users

question: does greetings support renters or only buyers ? 


Partners Onboarding 

1- Partner greetings , 
2- asking for their TG channel 
3-Fetching all messages related to assetType partner is providing
4-I think we will need hash code for messages to avoid duplicate assets
5-in the storage for the user we only store the raw descrption and then create a nice structred md file ( unique ) wich has the list of media files 

Note: as long as we can we never store any media files from the users / partners and so on , they can upload to some public clouad folder and share with us. i think it is legally better too



