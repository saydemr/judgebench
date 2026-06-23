from pydantic import BaseModel, Field


## Context Understanding Pydantic Classes
class GPSData(BaseModel):
    latitude: float = Field(..., description="Latitude of the restaurant")
    longitude: float = Field(..., description="Longitude of the restaurant")
    description: str = Field(..., description="District of the restaurant location")


class UserBlockInput(BaseModel):
    current_gps: GPSData = Field(..., description="GPS data of the user in car")
    date: str = Field(..., description="Current date in the user situtation in car")
    time: str = Field(..., description="Current time in the user situation in car")
    user_utterance: str = Field(..., description="User utterance for in car navigation")


class OpeningHours(BaseModel):
    monday: str = Field(..., description="Monday opening hours")
    tuesday: str = Field(..., description="Tuesday opening hours")
    wednesday: str = Field(..., description="Wednesday opening hours")
    thursday: str = Field(..., description="Thursday opening hours")
    friday: str = Field(..., description="Friday opening hours")
    saturday: str = Field(..., description="Saturday opening hours")
    sunday: str = Field(..., description="Sunday opening hours")


class SystemBlockInput(BaseModel):
    name: str = Field(..., description="This is the name of the restaurant")
    current_gps: GPSData = Field(..., description="GPS data of the restaurant")
    cost: str = Field(
        ..., description="Cost level of the restaurant (low / medium / high)"
    )
    opening_hours: OpeningHours = Field(
        ..., description="Opening hours for each day of the week"
    )
    cuisine_type: str = Field(
        ...,
        description="The type of cuisine offered by the restaurant, e.g., Italian, French etc.",
    )
    menu: str = Field(
        ...,
        description="Menu information of the restaurant, e.g. Tiramisu, Pizza, Steak etc.",
    )
    rating: float = Field(
        ..., description="Rating of the restaurant from 0 (worst) to 5 (best)"
    )
    distance_km: float = Field(..., description="Kilometers to destination")
    duration_min: int = Field(..., description="Duration in minutes to destination")


class ContextOutput(BaseModel):
    decision: str = Field(
        ...,
        description="Assess whether user block aligns with system block 'true' or whether it does not align 'false'",
    )
    reasoning: str = Field(
        ...,
        description="Give a short reason and explanation why it aligns or why it not aligns",
    )
    error_category: str = Field(
        ...,
        description="Give the category from the following: 'positive', 'location_error', 'time_error', 'cuisine_error', 'cost_error', 'rating_error'",
    )


IO_context_understanding_prompt_template = """
    You are a critical evaluator tasked with determining whether the information provided by a car navigation system (System Block) aligns correctly with the user's expressed needs in user utterance and user context (User Block). 

    ---
    You have to make a judgement (true or false) for the following case: 

    User Context in car:
    - Location:
        - Latitude: {current_gps_user_block.latitude}, 
        - Longitude: {current_gps_user_block.longitude}, 
        - Description: {current_gps_user_block.description}
    - Date: {date}
    - Time: {time}
    - User Utterance: {user_utterance}
    
    Restaurant recommendation from the system:
    - Restaurant Name: {name}
    - Location: 
        - Latitude: {current_gps_system_block.latitude}, 
        - Longitude: {current_gps_system_block.longitude}, 
        - Description: {current_gps_system_block.description}
    - Cuisine Type: {cuisine_type}
    - Menu: {menu}
    - Cost: {cost}
    - Rating: {rating}
    - Opening Hours: 
        - Monday: {opening_hours.monday}, 
        - Tuesday: {opening_hours.tuesday}, 
        - Wednesday: {opening_hours.wednesday}, 
        - Thursday: {opening_hours.thursday}, 
        - Friday: {opening_hours.friday},
        - Saturday: {opening_hours.saturday}, 
        - Sunday: {opening_hours.sunday},
    - Distance in kilometers: {distance_km},
    - Duration in minutes: {duration_min}
    ---

    Stick to the following rules:
    - Location: If the location is more than a 15-minute drive away, it is INCORRECT
    - Time: If the restaurant is closed at the time when the user is making the request, it is INCORRECT
    - Cost: If the mentioned cost in the user utterance is not matching the cost of the restaurant recommendation, it is INCORRECT
    - Rating: If the mentioned rating in the user utterance is not matching the rating of the restaurant recommendation, it is INCORRECT. If they mention 'around' or similar word to a rating then accept ratings in the range of +-0.2 around the requested rating.
    - Cuisine: If the mentioned cuisine in the user utterance is not matching the cuisine type of the restaurant recommendation, it is INCORRECT

    - Decision: If any of the above parameters are INCORRECT, the final decision is 'false'. If all parameters are correct, the final decision is 'true'.

    After looking at all examples, please now make your critical judgement whether the user block aligns with the system block, following the format instructions below. Please think about it carefully.
    Please respond strictly following the format specified below. Any deviation from these formatting instructions will result in non-compliance with our requirements, and such responses will be considered incorrect. 
    {format_instructions}. Make sure the output is always a valid Json format. Make sure the output is always a valid Json format. Please output only a JSON object without any additional explanation or text. Do not include any introductory or concluding remarks. 
"""

CoT_context_understanding_prompt_template_one_shot = """
    You are a critical evaluator tasked with determining whether the information provided by a car navigation system (System Block) aligns correctly with the user's expressed needs in user utterance and user context (User Block). 

    ---
    You have to make a judgement (true or false) for the following case: 

    User Context in car:
    - Location:
        - Latitude: {current_gps_user_block.latitude}, 
        - Longitude: {current_gps_user_block.longitude}, 
        - Description: {current_gps_user_block.description}
    - Date: {date}
    - Time: {time}
    - User Utterance: {user_utterance}
    
    Restaurant recommendation from the system:
    - Restaurant Name: {name}
    - Location: 
        - Latitude: {current_gps_system_block.latitude}, 
        - Longitude: {current_gps_system_block.longitude}, 
        - Description: {current_gps_system_block.description}
    - Cuisine Type: {cuisine_type}
    - Menu: {menu}
    - Cost: {cost}
    - Rating: {rating}
    - Opening Hours: 
        - Monday: {opening_hours.monday}, 
        - Tuesday: {opening_hours.tuesday}, 
        - Wednesday: {opening_hours.wednesday}, 
        - Thursday: {opening_hours.thursday}, 
        - Friday: {opening_hours.friday},
        - Saturday: {opening_hours.saturday}, 
        - Sunday: {opening_hours.sunday},
    - Distance in kilometers: {distance_km},
    - Duration in minutes: {duration_min}
    ---

    Stick to the following rules:
    - Location: If the location is more than a 15-minute drive away, it is INCORRECT
    - Time: If the restaurant is closed at the time when the user is making the request, it is INCORRECT
    - Cost: If the mentioned cost in the user utterance is not matching the cost of the restaurant recommendation, it is INCORRECT
    - Rating: If the mentioned rating in the user utterance is not matching the rating of the restaurant recommendation, it is INCORRECT. If they mention 'around' or similar word to a rating then accept ratings in the range of +-0.2 around the requested rating.
    - Cuisine: If the mentioned cuisine in the user utterance is not matching the cuisine type of the restaurant recommendation, it is INCORRECT

    - Decision: If any of the above parameters are INCORRECT, the final decision is 'false'. If all parameters are correct, the final decision is 'true'.
    ---

    Take the following cost error example as help for your decision: 

    User Block: 
    - Latitude: 48.15119909005971
    - Longitude: 11.56190872192383
    - Description: Munich, Maxvorstadt
    - Date: Wed, 18 Aug 2023
    - Time: 14:13
    - User Utterance: Can you locate a very budget-friendly restaurant with Italian food and at least a 3.6 rating?

    System Block: 
    - Restaurant Name: Luigis
    - Location
        - Latitude: 48.153199
        - Longitude:  11.563908
        - Description: Maxvorstadt, Munich
    - Cuisine Type: Italien
    - Menu: Pizza, Pasta, Dessert, Wine
    - Cost: high
    - Rating: 4.6
    - Opening Hours: 
        - Monday: 18:00-23:00
        - Tuesday:  18:00-23:00
        - Wednesday: 12:00-23:00
        - Thursday: 12:00-23:00
        - Friday: 12:00-23:00
        - Saturday: 12:00-23:00
        - Sunday: 12:00-23:00
    - Distance in kilometers: 0.6778
    - Duration in minutes: 3

    Take a step-by-step approach to evaluate whether the provided restaurant meets the user's request:
	1.	Location: The restaurant is only a 3-minute drive away, which is less than 15 minutes. Therefore, the location is CORRECT.
	2.	Time: The current time is 14:13 on Wednesday. The restaurant is open from 12:00 to 23:00 on Wednesdays, so it is currently open. Therefore, the time is CORRECT.
	3.	Cost: The user requested a “very budget-friendly” restaurant, indicating a low-cost preference. The restaurant has a high cost, which does not match the users request. Therefore, the cost is INCORRECT.
	4.	Rating: The user wants at least a 3.6 rating. The restaurant has a 4.6 rating, which meets this criterion. Therefore, the rating is CORRECT.
	5.	Cuisine: The user asked for Italian food, and the restaurant offers Italian cuisine. Therefore, the cuisine is CORRECT.

    Conclusion: Since the cost parameter is INCORRECT, the final decision is false.
    ---

    After looking at all examples, please now make your critical judgement whether the user block aligns with the system block, following the format instructions below. Please think about it carefully.
    Please respond strictly following the format specified below. Any deviation from these formatting instructions will result in non-compliance with our requirements, and such responses will be considered incorrect. 
    {format_instructions}. Make sure the output is always a valid Json format. Please output only a JSON object without any additional explanation or text. Do not include any introductory or concluding remarks. 
"""

CoT_context_understanding_prompt_template_one_shot_2 = """
    You are a critical evaluator tasked with determining whether the information provided by a car navigation system (System Block) aligns correctly with the user's expressed needs in user utterance and user context (User Block). 

    ---
    You have to make a judgement (true or false) for the following case: 

    User Context in car:
    - Location:
        - Latitude: {current_gps_user_block.latitude}, 
        - Longitude: {current_gps_user_block.longitude}, 
        - Description: {current_gps_user_block.description}
    - Date: {date}
    - Time: {time}
    - User Utterance: {user_utterance}
    
    Restaurant recommendation from the system:
    - Restaurant Name: {name}
    - Location: 
        - Latitude: {current_gps_system_block.latitude}, 
        - Longitude: {current_gps_system_block.longitude}, 
        - Description: {current_gps_system_block.description}
    - Cuisine Type: {cuisine_type}
    - Menu: {menu}
    - Cost: {cost}
    - Rating: {rating}
    - Opening Hours: 
        - Monday: {opening_hours.monday}, 
        - Tuesday: {opening_hours.tuesday}, 
        - Wednesday: {opening_hours.wednesday}, 
        - Thursday: {opening_hours.thursday}, 
        - Friday: {opening_hours.friday},
        - Saturday: {opening_hours.saturday}, 
        - Sunday: {opening_hours.sunday},
    - Distance in kilometers: {distance_km},
    - Duration in minutes: {duration_min}
    ---

    Stick to the following rules:
    - Location: If the location is more than a 15-minute drive away, it is INCORRECT
    - Time: If the restaurant is closed at the time when the user is making the request, it is INCORRECT
    - Cost: If the mentioned cost in the user utterance is not matching the cost of the restaurant recommendation, it is INCORRECT
    - Rating: If the mentioned rating in the user utterance is not matching the rating of the restaurant recommendation, it is INCORRECT. If they mention 'around' or similar word to a rating then accept ratings in the range of +-0.2 around the requested rating.
    - Cuisine: If the mentioned cuisine in the user utterance is not matching the cuisine type of the restaurant recommendation, it is INCORRECT

    - Decision: If any of the above parameters are INCORRECT, the final decision is 'false'. If all parameters are correct, the final decision is 'true'.
    ---

    Take the following cost error example as help for your decision: 

    User Block: 
    - Latitude: 48.15119909005971
    - Longitude: 11.56190872192383
    - Description: Munich, Maxvorstadt
    - Date: Wed, 18 Aug 2023
    - Time: 14:13
    - User Utterance: Can you locate a very budget-friendly restaurant with Italian food and at least a 3.6 rating?

    System Block: 
    - Restaurant Name: Luigis
    - Location
        - Latitude: 48.153199
        - Longitude:  11.563908
        - Description: Maxvorstadt, Munich
    - Cuisine Type: Italien
    - Menu: Pizza, Pasta, Dessert, Wine
    - Cost: high
    - Rating: 4.6
    - Opening Hours: 
        - Monday: 18:00-23:00
        - Tuesday:  18:00-23:00
        - Wednesday: 12:00-23:00
        - Thursday: 12:00-23:00
        - Friday: 12:00-23:00
        - Saturday: 12:00-23:00
        - Sunday: 12:00-23:00
    - Distance in kilometers: 0.6778
    - Duration in minutes: 3

    Take a step-by-step approach to evaluate whether the provided restaurant meets the user's request:
    - Step 1: Location - The user is located at latitude 48.151199 and longitude 11.561909 in Munich, Maxvorstadt. The restaurant is at latitude 48.153199 and longitude 11.563908, also in Maxvorstadt, Munich. The distance is 0.6778 kilometers, which takes about 3 minutes to drive. Is the location of the restaurant within a reasonable distance from the user (less than 15 minutes)? - Yes, it is, so it is correct.
    - Step 2: Time - The current time is Wednesday, 14:13. The restaurant's opening hours on Wednesday are from 12:00 to 23:00. Is the restaurant open at the time the user is searching? - Yes, it is open, thus it is correct.
    - Step 3: Cost - The user requested a "very budget-friendly" restaurant, indicating a preference for low-cost options. The restaurant has a high cost. Does the restaurants cost match the users budget-friendly request? No, it does not, since the user requested low cost, but high cost restaurant was recommended. Thus, it is incorrect.
    - Step 4: Rating - The user wants a restaurant with at least a 3.6 rating. The restaurant has a 4.6 rating. Does the restaurant meet the user's minimum rating requirement? - Yes, since 3.6 is bigger than 4.6 and user requested at least 3.6. Thus it is correct.
    - Step 5: Cuisine - The user asked for Italian cuisine. The restaurant offers Italian dishes like pizza, pasta, dessert, and wine. Does the restaurant offer the cuisine requested by the user? - Yes, the requested cuisine and recommended cuisine align, thus it is correct.

    Conclusion: Based on the analysis, if any parameter does not match the users request, the final decision should be "false." If all parameters match the user's request except cost, the decision is "false" due to the mismatch in budget.
    ---

    After looking at all examples, please now make your critical judgement whether the user block aligns with the system block, following the format instructions below. Please think about it carefully.
    Please respond strictly following the format specified below. Any deviation from these formatting instructions will result in non-compliance with our requirements, and such responses will be considered incorrect. 
    {format_instructions}. Make sure the output is always a valid Json format.
"""

CoT_context_understanding_prompt_template_three_shot = """
    You are a critical evaluator tasked with determining whether the information provided by a car navigation system (System Block) aligns correctly with the user's expressed needs in user utterance and user context (User Block). 

    ---
    You have to make a judgement (true or false) for the following case: 

    User Context in car:
    - Location:
        - Latitude: {current_gps_user_block.latitude}, 
        - Longitude: {current_gps_user_block.longitude}, 
        - Description: {current_gps_user_block.description}
    - Date: {date}
    - Time: {time}
    - User Utterance: {user_utterance}
    
    Restaurant recommendation from the system:
    - Restaurant Name: {name}
    - Location: 
        - Latitude: {current_gps_system_block.latitude}, 
        - Longitude: {current_gps_system_block.longitude}, 
        - Description: {current_gps_system_block.description}
    - Cuisine Type: {cuisine_type}
    - Menu: {menu}
    - Cost: {cost}
    - Rating: {rating}
    - Opening Hours: 
        - Monday: {opening_hours.monday}, 
        - Tuesday: {opening_hours.tuesday}, 
        - Wednesday: {opening_hours.wednesday}, 
        - Thursday: {opening_hours.thursday}, 
        - Friday: {opening_hours.friday},
        - Saturday: {opening_hours.saturday}, 
        - Sunday: {opening_hours.sunday},
    - Distance in kilometers: {distance_km},
    - Duration in minutes: {duration_min}
    ---

    Stick to the following rules:
    - Location: If the location is more than a 15-minute drive away, it is INCORRECT
    - Time: If the restaurant is closed at the time when the user is making the request, it is INCORRECT
    - Cost: If the mentioned cost in the user utterance is not matching the cost of the restaurant recommendation, it is INCORRECT
    - Rating: If the mentioned rating in the user utterance is not matching the rating of the restaurant recommendation, it is INCORRECT. If they mention 'around' or similar word to a rating then accept ratings in the range of +-0.2 around the requested rating.
    - Cuisine: If the mentioned cuisine in the user utterance is not matching the cuisine type of the restaurant recommendation, it is INCORRECT

    - Decision: If any of the above parameters are INCORRECT, the final decision is 'false'. If all parameters are correct, the final decision is 'true'.
    ---

    Take the following cost error example as help for your decision: 

    User Block: 
    - Latitude: 48.15119909005971
    - Longitude: 11.56190872192383
    - Description: Munich, Maxvorstadt
    - Date: Wed, 18 Aug 2023
    - Time: 14:13
    - User Utterance: Can you locate a very budget-friendly restaurant with Italian food and at least a 3.6 rating?

    System Block: 
    - Restaurant Name: Luigis
    - Location
        - Latitude: 48.153199
        - Longitude:  11.563908
        - Description: Maxvorstadt, Munich
    - Cuisine Type: Italien
    - Menu: Pizza, Pasta, Dessert, Wine
    - Cost: high
    - Rating: 4.6
    - Opening Hours: 
        - Monday: 18:00-23:00
        - Tuesday:  18:00-23:00
        - Wednesday: 12:00-23:00
        - Thursday: 12:00-23:00
        - Friday: 12:00-23:00
        - Saturday: 12:00-23:00
        - Sunday: 12:00-23:00
    - Distance in kilometers: 0.6778
    - Duration in minutes: 3

    Take a step-by-step approach to evaluate whether the provided restaurant meets the user's request:
	1.	Location: The restaurant is only a 3-minute drive away, which is less than 15 minutes. Therefore, the location is CORRECT.
	2.	Time: The current time is 14:13 on Wednesday. The restaurant is open from 12:00 to 23:00 on Wednesdays, so it is currently open. Therefore, the time is CORRECT.
	3.	Cost: The user requested a “very budget-friendly” restaurant, indicating a low-cost preference. The restaurant has a high cost, which does not match the users request. Therefore, the cost is INCORRECT.
	4.	Rating: The user wants at least a 3.6 rating. The restaurant has a 4.6 rating, which meets this criterion. Therefore, the rating is CORRECT.
	5.	Cuisine: The user asked for Italian food, and the restaurant offers Italian cuisine. Therefore, the cuisine is CORRECT.

    Conclusion: Since the cost parameter is INCORRECT, the final decision is false.
    ---

    Take the following positive example as help for your decision: 
    
    User Block: 
    - Latitude: 52.497515324667674
    - Longitude: 13.420960604021236
    - Description: Berlin, Kreuzberg
    - Date: Sat, 07 Sep 2024
    - Time: 18:07
    - User Utterance: Can you locate a spot where I can get Burgers, with medium prices and a rating over 4?

    System Block: 
    - Restaurant Name: Bruger Brazzo
    - Location
        - Latitude: 52.489506
        - Longitude:  13.422507
        - Description: Berlin, Kreuzberg
    - Cuisine Type: American
    - Menu: Burger, Fries, Softdrinks
    - Cost: medium
    - Rating: 4.2
    - Opening Hours: 
        - Monday: Closed
        - Tuesday:  08:00-20:00
        - Wednesday: 08:00-20:00
        - Thursday: 08:00-20:00
        - Friday: 08:00-20:00
        - Saturday: 08:00-22:00
        - Sunday: 08:00-22:00
    - Distance in kilometers: 1.4830999999999999
    - Duration in minutes: 6

    Take a step-by-step approach to evaluate whether the provided restaurant meets the user's request:
    1.	Location: The restaurant is a 6-minute drive away, which is less than the 15-minute threshold. Therefore, the location is CORRECT.
	2.	Time: The current time is 18:07 on Saturday. According to the opening hours, the restaurant closes at 22:00 on Saturdays. Thus, the restaurant is open at the time of user request. Therefore, the time is CORRECT.
	3.	Cost: The user requested a restaurant with “medium prices,” and the restaurants cost is listed as “medium.” Therefore, the cost is CORRECT.
	4.	Rating: The user asked for a rating “over 4.” The restaurant has a rating of 4.2, which aligns with the requested rating. Therefore, the rating is CORRECT.
	5.	Cuisine: The user is looking for a place to get “Burgers.” The restaurants cuisine type is “American,” and the menu includes “Burger, Fries, Softdrinks.” This matches the users request. Therefore, the cuisine is CORRECT.

    Since all parameters are correct, the final decision is true.
    ---

    Take the following cuisine error example as help for your decision: 

    User Block: 
    - Latitude: 48.151199
    - Longitude: 11.56190
    - Description: Munich, Maxvorstadt
    - Date: Fri, 18 Aug 2023
    - Time: 18:13
    - User Utterance: Help me find a restaurant that german meals, is very easy on the wallet, and has a rating of at least 4.2.

    System Block: 
    - Restaurant Name: Sophia's Restaurant & Bar
    - Location
        - Latitude: 48.14251708984375
        - Longitude: 11.564806938171387
        - Description: Munich, Maxvorstadt
    - Cuisine Type: Italien
    - Menu: Pasta, Pizza, Desserts, Drinks
    - Cost: low
    - Rating: 4.3
    - Opening Hours: 
        - Monday: 18:00-23:00
        - Tuesday:  18:00-23:00
        - Wednesday: 18:00-23:00
        - Thursday: 18:00-23:00
        - Friday: 18:00-23:00
        - Saturday: 18:00-23:00
        - Sunday: 18:00-23:00
    - Distance in kilometers: 2.3
    - Duration in minutes: 9

    Take a step-by-step approach to evaluate whether the provided restaurant meets the user's request:
    1.	Location: The restaurant is a 9-minute drive away, which is less than the 15-minute threshold. Therefore, the location is CORRECT.
	2.	Time: The current time is 18:13 on Friday. According to the opening hours, the restaurant is open from 18:00 to 23:00 on Fridays. Thus, the restaurant is open at the time of the users request. Therefore, the time is CORRECT.
	3.	Cost: The user wants a restaurant that is “very easy on the wallet” (low cost), and the restaurants cost is listed as low. Therefore, the cost is CORRECT.
	4.	Rating: The user requests a rating of at least 4.2. The restaurant has a rating of 4.3, which meets the requested rating. Therefore, the rating is CORRECT.
	5.	Cuisine: The user is looking for German meals. The restaurant offers Italian cuisine, which does not match the users request. Therefore, the cuisine is INCORRECT.

    Conclusion: Since the cuisine parameter is INCORRECT, the final decision is false.
    ---

    After looking at all examples, please now make your critical judgement whether the user block aligns with the system block, following the format instructions below. Please think about it carefully.
    Please respond strictly following the format specified below. Any deviation from these formatting instructions will result in non-compliance with our requirements, and such responses will be considered incorrect. 
    {format_instructions}. Make sure the output is always a valid Json format. Make sure the output is always a valid Json format. Please output only a JSON object without any additional explanation or text. Do not include any introductory or concluding remarks!!!
"""

CoT_context_understanding_prompt_template_five_shot = """

    You are a critical evaluator tasked with determining whether the information provided by a car navigation system (System Block) aligns correctly with the user's expressed needs in user utterance and user context (User Block). 

    You have to make a judgement (true or false) for the following case: 

    User Context in car:
    - Location:
        - Latitude: {current_gps_user_block.latitude}, 
        - Longitude: {current_gps_user_block.longitude}, 
        - Description: {current_gps_user_block.description}
    - Date: {date}
    - Time: {time}
    - User Utterance: {user_utterance}
    
    Restaurant recommendation from the system:
    - Restaurant Name: {name}
    - Location: 
        - Latitude: {current_gps_system_block.latitude}, 
        - Longitude: {current_gps_system_block.longitude}, 
        - Description: {current_gps_system_block.description}
    - Cuisine Type: {cuisine_type}
    - Menu: {menu}
    - Cost: {cost}
    - Rating: {rating}
    - Opening Hours: 
        - Monday: {opening_hours.monday}, 
        - Tuesday: {opening_hours.tuesday}, 
        - Wednesday: {opening_hours.wednesday}, 
        - Thursday: {opening_hours.thursday}, 
        - Friday: {opening_hours.friday},
        - Saturday: {opening_hours.saturday}, 
        - Sunday: {opening_hours.sunday},
    - Distance in kilometers: {distance_km},
    - Duration in minutes: {duration_min}

    Stick to the following rules:
    - Location: If the location is more than a 15-minute drive away, it is INCORRECT
    - Time: If the restaurant is closed at the time when the user is making the request, it is INCORRECT
    - Cost: If the mentioned cost in the user utterance is not matching the cost of the restaurant recommendation, it is INCORRECT
    - Rating: If the mentioned rating in the user utterance is not matching the rating of the restaurant recommendation, it is INCORRECT. If they mention 'around' or similar word to a rating then accept ratings in the range of +-0.2 around the requested rating.
    - Cuisine: If the mentioned cuisine in the user utterance is not matching the cuisine type of the restaurant recommendation, it is INCORRECT

    - Final Decision: If any of the above parameters are INCORRECT, the final decision is 'false'. If all parameters are correct, the final decision is 'true'.

    In the following examples, I will demonstrate how to evaluate whether the provided restaurant meets the users request. It should guide your decision-making process:

    User Block: 
    - Latitude: 48.15119909005971
    - Longitude: 11.56190872192383
    - Description: Munich, Maxvorstadt
    - Date: Wed, 18 Aug 2023
    - Time: 14:13
    - User Utterance: Can you locate a very budget-friendly restaurant with Italian food and at least a 3.6 rating?

    System Block: 
    - Restaurant Name: Luigis
    - Location
        - Latitude: 48.153199
        - Longitude:  11.563908
        - Description: Maxvorstadt, Munich
    - Cuisine Type: Italien
    - Menu: Pizza, Pasta, Dessert, Wine
    - Cost: high
    - Rating: 4.6
    - Opening Hours: 
        - Monday: 18:00-23:00
        - Tuesday:  18:00-23:00
        - Wednesday: 12:00-23:00
        - Thursday: 12:00-23:00
        - Friday: 12:00-23:00
        - Saturday: 12:00-23:00
        - Sunday: 12:00-23:00
    - Distance in kilometers: 0.6778
    - Duration in minutes: 3

    Take a step-by-step approach to evaluate whether the provided restaurant meets the user's request:
	1.	Location: The restaurant is only a 3-minute drive away, which is less than 15 minutes. Therefore, the location is CORRECT.
	2.	Time: The current time is 14:13 on Wednesday. The restaurant is open from 12:00 to 23:00 on Wednesdays, so it is currently open. Therefore, the time is CORRECT.
	3.	Cost: The user requested a “very budget-friendly” restaurant, indicating a low-cost preference. The restaurant has a high cost, which does not match the users request. Therefore, the cost is INCORRECT.
	4.	Rating: The user wants at least a 3.6 rating. The restaurant has a 4.6 rating, which meets this criterion. Therefore, the rating is CORRECT.
	5.	Cuisine: The user asked for Italian food, and the restaurant offers Italian cuisine. Therefore, the cuisine is CORRECT.

    Conclusion: Since the cost parameter is INCORRECT, the final decision is false.
    ---

    Take the following positive example as help for your decision: 
    
    User Block: 
    - Latitude: 52.497515324667674
    - Longitude: 13.420960604021236
    - Description: Berlin, Kreuzberg
    - Date: Sat, 07 Sep 2024
    - Time: 18:07
    - User Utterance: Can you locate a spot where I can get Burgers, with medium prices and a rating over 4?

    System Block: 
    - Restaurant Name: Bruger Brazzo
    - Location
        - Latitude: 52.489506
        - Longitude:  13.422507
        - Description: Berlin, Kreuzberg
    - Cuisine Type: American
    - Menu: Burger, Fries, Softdrinks
    - Cost: medium
    - Rating: 4.2
    - Opening Hours: 
        - Monday: Closed
        - Tuesday:  08:00-20:00
        - Wednesday: 08:00-20:00
        - Thursday: 08:00-20:00
        - Friday: 08:00-20:00
        - Saturday: 08:00-22:00
        - Sunday: 08:00-22:00
    - Distance in kilometers: 1.4830999999999999
    - Duration in minutes: 6

    Take a step-by-step approach to evaluate whether the provided restaurant meets the user's request:
    1.	Location: The restaurant is a 6-minute drive away, which is less than the 15-minute threshold. Therefore, the location is CORRECT.
	2.	Time: The current time is 18:07 on Saturday. According to the opening hours, the restaurant closes at 22:00 on Saturdays. Thus, the restaurant is open at the time of user request. Therefore, the time is CORRECT.
	3.	Cost: The user requested a restaurant with “medium prices,” and the restaurants cost is listed as “medium.” Therefore, the cost is CORRECT.
	4.	Rating: The user asked for a rating “over 4.” The restaurant has a rating of 4.2, which aligns with the requested rating. Therefore, the rating is CORRECT.
	5.	Cuisine: The user is looking for a place to get “Burgers.” The restaurants cuisine type is “American,” and the menu includes “Burger, Fries, Softdrinks.” This matches the users request. Therefore, the cuisine is CORRECT.

    Since all parameters are correct, the final decision is true.
    ---

    Take the following cuisine error example as help for your decision: 

    User Block: 
    - Latitude: 48.151199
    - Longitude: 11.56190
    - Description: Munich, Maxvorstadt
    - Date: Fri, 18 Aug 2023
    - Time: 18:13
    - User Utterance: Help me find a restaurant that german meals, is very easy on the wallet, and has a rating of at least 4.2.

    System Block: 
    - Restaurant Name: Sophia's Restaurant & Bar
    - Location
        - Latitude: 48.14251708984375
        - Longitude: 11.564806938171387
        - Description: Munich, Maxvorstadt
    - Cuisine Type: Italien
    - Menu: Pasta, Pizza, Desserts, Drinks
    - Cost: low
    - Rating: 4.3
    - Opening Hours: 
        - Monday: 18:00-23:00
        - Tuesday:  18:00-23:00
        - Wednesday: 18:00-23:00
        - Thursday: 18:00-23:00
        - Friday: 18:00-23:00
        - Saturday: 18:00-23:00
        - Sunday: 18:00-23:00
    - Distance in kilometers: 2.3
    - Duration in minutes: 9

    Take a step-by-step approach to evaluate whether the provided restaurant meets the user's request:
    1.	Location: The restaurant is a 9-minute drive away, which is less than the 15-minute threshold. Therefore, the location is CORRECT.
	2.	Time: The current time is 18:13 on Friday. According to the opening hours, the restaurant is open from 18:00 to 23:00 on Fridays. Thus, the restaurant is open at the time of the users request. Therefore, the time is CORRECT.
	3.	Cost: The user wants a restaurant that is “very easy on the wallet” (low cost), and the restaurants cost is listed as low. Therefore, the cost is CORRECT.
	4.	Rating: The user requests a rating of at least 4.2. The restaurant has a rating of 4.3, which meets the requested rating. Therefore, the rating is CORRECT.
	5.	Cuisine: The user is looking for German meals. The restaurant offers Italian cuisine, which does not match the users request. Therefore, the cuisine is INCORRECT.

    Conclusion: Since the cuisine parameter is INCORRECT, the final decision is false.
    ---

    Take the following time error example as help for your decision: 

    User Block: 
    - Latitude: 48.128861497246476
    - Longitude: 11.571006774902344
    - Description: Munich, Isarvorstadt
    - Date: Sun, 23 Jul 2023
    - Time: 21:12
    - User Utterance: I need a restaurant with filling, mediterranean, very affordable food and a rating above 3.8. Can you help?

    System Block: 
    - Restaurant Name: Gazzo
    - Location
        - Latitude: 48.13101972155441
        - Longitude: 11.580836530372856
        - Description: Munich, Glockenbach
    - Cuisine Type: Italien
    - Menu: Pizza, Pasta, Wine, Tiramisu
    - Cost: low
    - Rating: 4.0
    - Opening Hours: 
        - Monday: 11:00-22:00
        - Tuesday:  11:00-22:00
        - Wednesday: 11:00-22:00
        - Thursday: 11:00-22:00
        - Friday: 11:00-00:00
        - Saturday: 11:00-00:00
        - Sunday: 11:00-21:00
    - Distance in kilometers: 1.1
    - Duration in minutes: 5
    
    Take a step-by-step approach to evaluate whether the provided restaurant meets the user's request:
    1.	Location: The restaurant is a 5-minute drive away, which is less than the 15-minute threshold. Therefore, the location is CORRECT.
	2.	Time: The current time is 21:12 on Sunday. According to the opening hours, the restaurant closes at 21:00 on Sundays. Therefore, the restaurant is closed at the time of the users request. Therefore, the time is INCORRECT.
	3.	Cost: The user wants a restaurant that is “very affordable” (low cost), and the restaurants cost is listed as low. Therefore, the cost is CORRECT.
	4.	Rating: The user requests a rating above 3.8. The restaurant has a rating of 4.0, which meets the requested rating. Therefore, the rating is CORRECT.
	5.	Cuisine: The user asks for “Mediterranean” food. The restaurant offers Italian cuisine, which is considered part of Mediterranean cuisine. Therefore, the cuisine is CORRECT.

    Conclusion: Since the time parameter is INCORRECT, the final decision is false.
    ---

    Take the following location error example as help for your decision: 

    User Block: 
    - Latitude: 52.50205441987642
    - Longitude: 13.322704758293828
    - Description: Berlin, Charlottenburg
    - Date: Wed, 15 Nov 2023
    - Time: 13:20
    - User Utterance: Please help me find a restaurant offering vegan and vegetarian dishes, with medium costs, and a decent rating above 4.2

    System Block: 
    - Restaurant Name: Copenhagen Deli
    - Location
        - Latitude: 52.67205441987642
        - Longitude: 13.492704758293828
        - Description: Berlin, Reinickendorf
    - Cuisine Type: Vegan & Vegeterian Salads
    - Menu: Breakfast, Baguettes, Bread, Coffee, Cake, Avocado, Salads
    - Cost: medium
    - Rating: 4.5
    - Opening Hours: 
        - Monday: Closed
        - Tuesday:  09:30-18:00
        - Wednesday: 09:30-18:00
        - Thursday: 09:30-18:00
        - Friday: 09:30-18:00
        - Saturday: 09:30-18:00
        - Sunday: 09:30-18:00
    - Distance in kilometers: 15.3
    - Duration in minutes: 32

    Take a step-by-step approach to evaluate whether the provided restaurant meets the user's request:
   	1.	Location: The restaurant is a 32-minute drive away, which is greater than the 15-minute threshold. Therefore, the location is INCORRECT.
	2.	Time: The current time is 13:20 on Wednesday. According to the opening hours, the restaurant is open from 09:30 to 18:00 on Wednesdays. Therefore, the time is CORRECT.
	3.	Cost: The user wants “medium costs,” and the restaurants cost is listed as medium. Therefore, the cost is CORRECT.
	4.	Rating: The user requests a rating above 4.2. The restaurant has a rating of 4.5, which meets the requested rating. Therefore, the rating is CORRECT.
	5.	Cuisine: The user asks for “vegan and vegetarian dishes.” The restaurant offers Vegan & Vegetarian Salads, which matches the users request. Therefore, the cuisine is CORRECT.

    Conclusion: Since the location parameter is INCORRECT, the final decision is false.
    ---

    After looking at all examples, please now make your critical judgement whether the user block aligns with the system block, following the format instructions below. Please think about it carefully.
    Please respond strictly following the format specified below. Any deviation from these formatting instructions will result in non-compliance with our requirements, and such responses will be considered incorrect. 
    {format_instructions}. Make sure the output is always a valid Json format. Make sure the output is always a valid Json format. Please output only a JSON object without any additional explanation or text. Do not include any introductory or concluding remarks!!!
"""

io_new = """
    You are a critical evaluator tasked with determining whether the information provided by a car navigation system (**System Block**) aligns correctly with the user's expressed needs in the **User Block**.

    **Instructions:**

    1. Carefully read the **User Block** and **System Block**.
    2. Evaluate each of the following parameters step by step:
    - **Location**: If the duration in minutes is more than 15, it is **INCORRECT**.
    - **Time**: If the restaurant is closed at the time of the user's request, it is **INCORRECT**.
    - **Cost**: If the cost in the user utterance does not match the cost of the restaurant, it is **INCORRECT**.
    - **Rating**: If the rating in the user utterance does not match the restaurant's rating, it is **INCORRECT**. If the user mentions "around" or similar words, accept ratings within ±0.2 of the requested rating.
    - **Cuisine**: If the cuisine in the user utterance does not match the restaurant's cuisine type, it is **INCORRECT**.
    3. Make a final decision:
    - If any parameter is **INCORRECT**, the final decision is **false**.
    - If all parameters are **CORRECT**, the final decision is **true**.

    ---

    Now, please evaluate the following case:

    **User Block:**
    - Location:
    - Latitude: {current_gps_user_block.latitude}
    - Longitude: {current_gps_user_block.longitude}
    - Description: {current_gps_user_block.description}
    - Date: {date}
    - Time: {time}
    - User Utterance: "{user_utterance}"

    **System Block:**
    - Restaurant Name: {name}
    - Location: 
        - Latitude: {current_gps_system_block.latitude}, 
        - Longitude: {current_gps_system_block.longitude}, 
        - Description: {current_gps_system_block.description}
    - Cuisine Type: {cuisine_type}
    - Menu: {menu}
    - Cost: {cost}
    - Rating: {rating}
    - Opening Hours: 
        - Monday: {opening_hours.monday}, 
        - Tuesday: {opening_hours.tuesday}, 
        - Wednesday: {opening_hours.wednesday}, 
        - Thursday: {opening_hours.thursday}, 
        - Friday: {opening_hours.friday},
        - Saturday: {opening_hours.saturday}, 
        - Sunday: {opening_hours.sunday},
    - Distance in kilometers: {distance_km},
    - Duration in minutes: {duration_min}

    After looking at all examples, please now make your critical judgement whether the user block aligns with the system block, following the format instructions below. Please think about it carefully.
    Please respond strictly following the format specified below. Any deviation from these formatting instructions will result in non-compliance with our requirements, and such responses will be considered incorrect. 
    {format_instructions}. Make sure the output is always a valid Json format. Make sure the output is always a valid Json format. Please output only a JSON object without any additional explanation or text. Do not include any introductory or concluding remarks!!!

"""

cot_1_new = """

    You are a critical evaluator tasked with determining whether the information provided by a car navigation system (**System Block**) aligns correctly with the user's expressed needs in the **User Block**.

    **Instructions:**

    1. Carefully read the **User Block** and **System Block**.
    2. Evaluate each of the following parameters step by step:
    - **Location**: If the duration in minutes is more than 15, it is **INCORRECT**.
    - **Time**: If the restaurant is closed at the time of the user's request, it is **INCORRECT**.
    - **Cost**: If the cost in the user utterance does not match the cost of the restaurant, it is **INCORRECT**.
    - **Rating**: If the rating in the user utterance does not match the restaurant's rating, it is **INCORRECT**. If the user mentions "around" or similar words, accept ratings within ±0.2 of the requested rating.
    - **Cuisine**: If the cuisine in the user utterance does not match the restaurant's cuisine type, it is **INCORRECT**.
    3. Make a final decision:
    - If any parameter is **INCORRECT**, the final decision is **false**.
    - If all parameters are **CORRECT**, the final decision is **true**.

    **Examples:**

    ---

    **Example 1: Cost Error**

    **User Block:**
    - Location:
        - Latitude: 48.15119909005971
        - Longitude: 11.56190872192383
        - Description: Munich, Maxvorstadt
    - Date: Wed, 18 Aug 2023
    - Time: 14:13
    - User Utterance: "Can you locate a very budget-friendly restaurant with Italian food and at least a 3.6 rating?"

    **System Block:**
    - Restaurant Name: Luigis
    - Location:
        - Latitude: 48.153199
        - Longitude: 11.563908
        - Description: Maxvorstadt, Munich
    - Cuisine Type: Italian
    - Menu: Pizza, Pasta, Dessert, Wine
    - Cost: high
    - Rating: 4.6
    - **Opening Hours:**
        - Monday: 18:00-23:00
        - Tuesday: 18:00-23:00
        - Wednesday: 12:00-23:00
        - Thursday: 12:00-23:00
        - Friday: 12:00-23:00
        - Saturday: 12:00-23:00
        - Sunday: 12:00-23:00
    - Distance in kilometers: 0.6778
    - Duration in minutes: 3

    **Evaluation:**
    1. **Location**: 3 minutes < 15 minutes ⇒ **CORRECT**
    2. **Time**: At 14:13 on Wednesday, the user requests a restaurant. The restaurants Wednesday opening hours are from 12:00 to 23:00. Since the current time (14:13) is between the opening hours, the restaurant is open when the user makes the request. Thus, the time parameter is CORRECT.
    3. **Cost**: User wants "very budget-friendly" (low); restaurant cost is "high" ⇒ **INCORRECT**
    4. **Rating**: User wants at least 3.6; restaurant rating is 4.6 ⇒ **CORRECT**
    5. **Cuisine**: User wants Italian; restaurant offers Italian ⇒ **CORRECT**

    **Conclusion**: Since **Cost** is **INCORRECT**, the final decision is **false**.

    ---

    Now, please evaluate the following case:

    **User Block:**
    - Location:
    - Latitude: {current_gps_user_block.latitude}
    - Longitude: {current_gps_user_block.longitude}
    - Description: {current_gps_user_block.description}
    - Date: {date}
    - Time: {time}
    - User Utterance: "{user_utterance}"

    **System Block:**
    - Restaurant Name: {name}
    - Location: 
        - Latitude: {current_gps_system_block.latitude}, 
        - Longitude: {current_gps_system_block.longitude}, 
        - Description: {current_gps_system_block.description}
    - Cuisine Type: {cuisine_type}
    - Menu: {menu}
    - Cost: {cost}
    - Rating: {rating}
    - Opening Hours: 
        - Monday: {opening_hours.monday}, 
        - Tuesday: {opening_hours.tuesday}, 
        - Wednesday: {opening_hours.wednesday}, 
        - Thursday: {opening_hours.thursday}, 
        - Friday: {opening_hours.friday},
        - Saturday: {opening_hours.saturday}, 
        - Sunday: {opening_hours.sunday},
    - Distance in kilometers: {distance_km},
    - Duration in minutes: {duration_min}

    After looking at all examples, please now make your critical judgement whether the user block aligns with the system block, following the format instructions below. Please think about it carefully.
    Please respond strictly following the format specified below. Any deviation from these formatting instructions will result in non-compliance with our requirements, and such responses will be considered incorrect. 
    {format_instructions}. Make sure the output is always a valid Json format. Make sure the output is always a valid Json format. Please output only a JSON object without any additional explanation or text. Do not include any introductory or concluding remarks!!!
"""

## COT-3 New

cot_3_new = """

    You are a critical evaluator tasked with determining whether the information provided by a car navigation system (**System Block**) aligns correctly with the user's expressed needs in the **User Block**.

    **Instructions:**

    1. Carefully read the **User Block** and **System Block**.
    2. Evaluate each of the following parameters step by step:
    - **Location**: If the duration in minutes is more than 15, it is **INCORRECT**.
    - **Time**: If the restaurant is closed at the time of the user's request, it is **INCORRECT**.
    - **Cost**: If the cost in the user utterance does not match the cost of the restaurant, it is **INCORRECT**.
    - **Rating**: If the rating in the user utterance does not match the restaurant's rating, it is **INCORRECT**. If the user mentions "around" or similar words, accept ratings within ±0.2 of the requested rating.
    - **Cuisine**: If the cuisine in the user utterance does not match the restaurant's cuisine type, it is **INCORRECT**.
    3. Make a final decision:
    - If any parameter is **INCORRECT**, the final decision is **false**.
    - If all parameters are **CORRECT**, the final decision is **true**.

    **Examples:**

    ---

    **Example 1: Cost Error**

    **User Block:**
    - Location:
        - Latitude: 48.15119909005971
        - Longitude: 11.56190872192383
        - Description: Munich, Maxvorstadt
    - Date: Wed, 18 Aug 2023
    - Time: 14:13
    - User Utterance: "Can you locate a very budget-friendly restaurant with Italian food and at least a 3.6 rating?"

    **System Block:**
    - Restaurant Name: Luigis
    - Location:
        - Latitude: 48.153199
        - Longitude: 11.563908
        - Description: Maxvorstadt, Munich
    - Cuisine Type: Italian
    - Menu: Pizza, Pasta, Dessert, Wine
    - Cost: high
    - Rating: 4.6
    - **Opening Hours:**
        - Monday: 18:00-23:00
        - Tuesday: 18:00-23:00
        - Wednesday: 12:00-23:00
        - Thursday: 12:00-23:00
        - Friday: 12:00-23:00
        - Saturday: 12:00-23:00
        - Sunday: 12:00-23:00
    - Distance in kilometers: 0.6778
    - Duration in minutes: 3

    **Evaluation:**
    1. **Location**: 3 minutes < 15 minutes ⇒ **CORRECT**
    2. **Time**: At 14:13 on Wednesday, the user requests a restaurant. The restaurants Wednesday opening hours are from 12:00 to 23:00. Since the current time (14:13) is between the opening hours, the restaurant is open when the user makes the request. Thus, the time parameter is CORRECT.
    3. **Cost**: User wants "very budget-friendly" (low); restaurant cost is "high" ⇒ **INCORRECT**
    4. **Rating**: User wants at least 3.6; restaurant rating is 4.6 ⇒ **CORRECT**
    5. **Cuisine**: User wants Italian; restaurant offers Italian ⇒ **CORRECT**

    **Conclusion**: Since **Cost** is **INCORRECT**, the final decision is **false**.

    ---

    **Example 2: Positive Match**

    **User Block:**
    - Location:
        - Latitude: 52.497515324667674
        - Longitude: 13.420960604021236
        - Description: Berlin, Kreuzberg
    - Date: Sat, 07 Sep 2024
    - Time: 18:07
    - User Utterance: "Can you locate a spot where I can get burgers, with medium prices and a rating over 4?"

    **System Block:**
    - Restaurant Name: Burger Brazzo
    - Location:
        - Latitude: 52.489506
        - Longitude: 13.422507
        - Description: Berlin, Kreuzberg
    - Cuisine Type: American
    - Menu: Burgers, Fries, Soft Drinks
    - Cost: medium
    - Rating: 4.2
    - **Opening Hours:**
        - Monday: Closed
        - Tuesday: 08:00-20:00
        - Wednesday: 08:00-20:00
        - Thursday: 08:00-20:00
        - Friday: 08:00-20:00
        - Saturday: 08:00-22:00
        - Sunday: 08:00-22:00
    - Distance in kilometers: 1.4831
    - Duration in minutes: 6

    **Evaluation:**
    1. **Location**: 6 minutes < 15 minutes ⇒ **CORRECT**
    2. **Time**: At 18:07 on Saturday, the user requests a restaurant. The restaurants Saturday opening hours are from 08:00 to 22:00. Since the current time (18:07) is between the opening hours, the restaurant is open when the user makes the request. Thus, the time parameter is CORRECT.
    3. **Cost**: User wants "medium prices"; restaurant cost is "medium" ⇒ **CORRECT**
    4. **Rating**: User wants over 4; restaurant rating is 4.2 ⇒ **CORRECT**
    5. **Cuisine**: User wants burgers; restaurant offers burgers ⇒ **CORRECT**

    **Conclusion**: All parameters are **CORRECT**; the final decision is **true**.

    ---

    **Example 3: Cuisine Error**

    **User Block:**
    - Location:
        - Latitude: 48.151199
        - Longitude: 11.56190
        - Description: Munich, Maxvorstadt
    - Date: Fri, 18 Aug 2023
    - Time: 18:13
    - User Utterance: "Help me find a restaurant that serves German meals, is very easy on the wallet, and has a rating of at least 4.2."

    **System Block:**
    - Restaurant Name: Sophia's Restaurant & Bar
    - Location:
        - Latitude: 48.14251708984375
        - Longitude: 11.564806938171387
        - Description: Munich, Maxvorstadt
    - Cuisine Type: Italian
    - Menu: Pasta, Pizza, Desserts, Drinks
    - Cost: low
    - Rating: 4.3
    - **Opening Hours:**
        - Monday: 18:00-23:00
        - Tuesday: 18:00-23:00
        - Wednesday: 18:00-23:00
        - Thursday: 18:00-23:00
        - Friday: 18:00-23:00
        - Saturday: 18:00-23:00
        - Sunday: 18:00-23:00
    - Distance in kilometers: 2.3
    - Duration in minutes: 9

    **Evaluation:**
    1. **Location**: 9 minutes < 15 minutes ⇒ **CORRECT**
    2. **Time**: At 18:13 on Friday, the user requests a restaurant. The restaurants Friday opening hours are from 18:00 to 23:00. Since the current time (18:13) is between the opening hours, the restaurant is open when the user makes the request. Thus, the time parameter is CORRECT.
    3. **Cost**: User wants "very easy on the wallet" (low); restaurant cost is "low" ⇒ **CORRECT**
    4. **Rating**: User wants at least 4.2; restaurant rating is 4.3 ⇒ **CORRECT**
    5. **Cuisine**: User wants German meals; restaurant offers Italian ⇒ **INCORRECT**

    **Conclusion**: Since **Cuisine** is **INCORRECT**, the final decision is **false**.

    ---

    Now, please evaluate the following case:

    **User Block:**
    - Location:
    - Latitude: {current_gps_user_block.latitude}
    - Longitude: {current_gps_user_block.longitude}
    - Description: {current_gps_user_block.description}
    - Date: {date}
    - Time: {time}
    - User Utterance: "{user_utterance}"

    **System Block:**
    - Restaurant Name: {name}
    - Location: 
        - Latitude: {current_gps_system_block.latitude}, 
        - Longitude: {current_gps_system_block.longitude}, 
        - Description: {current_gps_system_block.description}
    - Cuisine Type: {cuisine_type}
    - Menu: {menu}
    - Cost: {cost}
    - Rating: {rating}
    - Opening Hours: 
        - Monday: {opening_hours.monday}, 
        - Tuesday: {opening_hours.tuesday}, 
        - Wednesday: {opening_hours.wednesday}, 
        - Thursday: {opening_hours.thursday}, 
        - Friday: {opening_hours.friday},
        - Saturday: {opening_hours.saturday}, 
        - Sunday: {opening_hours.sunday},
    - Distance in kilometers: {distance_km},
    - Duration in minutes: {duration_min}

    After looking at all examples, please now make your critical judgement whether the user block aligns with the system block, following the format instructions below. Please think about it carefully.
    Please respond strictly following the format specified below. Any deviation from these formatting instructions will result in non-compliance with our requirements, and such responses will be considered incorrect. 
    {format_instructions}. Make sure the output is always a valid Json format. Make sure the output is always a valid Json format. Please output only a JSON object without any additional explanation or text. Do not include any introductory or concluding remarks!!!
"""


cot_5_new = """

    You are a critical evaluator tasked with determining whether the information provided by a car navigation system (**System Block**) aligns correctly with the user's expressed needs in the **User Block**.

    **Instructions:**

    1. Carefully read the **User Block** and **System Block**.
    2. Evaluate each of the following parameters step by step:
    - **Location**: If the duration in minutes is more than 15, it is **INCORRECT**.
    - **Time**: If the restaurant is closed at the time of the user's request, it is **INCORRECT**.
    - **Cost**: If the cost in the user utterance does not match the cost of the restaurant, it is **INCORRECT**.
    - **Rating**: If the rating in the user utterance does not match the restaurant's rating, it is **INCORRECT**. If the user mentions "around" or similar words, accept ratings within ±0.2 of the requested rating.
    - **Cuisine**: If the cuisine in the user utterance does not match the restaurant's cuisine type, it is **INCORRECT**.
    3. Make a final decision:
    - If any parameter is **INCORRECT**, the final decision is **false**.
    - If all parameters are **CORRECT**, the final decision is **true**.

    **Examples:**

    ---

    **Example 1: Cost Error**

    **User Block:**
    - Location:
        - Latitude: 48.15119909005971
        - Longitude: 11.56190872192383
        - Description: Munich, Maxvorstadt
    - Date: Wed, 18 Aug 2023
    - Time: 14:13
    - User Utterance: "Can you locate a very budget-friendly restaurant with Italian food and at least a 3.6 rating?"

    **System Block:**
    - Restaurant Name: Luigis
    - Location:
        - Latitude: 48.153199
        - Longitude: 11.563908
        - Description: Maxvorstadt, Munich
    - Cuisine Type: Italian
    - Menu: Pizza, Pasta, Dessert, Wine
    - Cost: high
    - Rating: 4.6
    - **Opening Hours:**
        - Monday: 18:00-23:00
        - Tuesday: 18:00-23:00
        - Wednesday: 12:00-23:00
        - Thursday: 12:00-23:00
        - Friday: 12:00-23:00
        - Saturday: 12:00-23:00
        - Sunday: 12:00-23:00
    - Distance in kilometers: 0.6778
    - Duration in minutes: 3

    **Evaluation:**
    1. **Location**: 3 minutes < 15 minutes ⇒ **CORRECT**
    2. **Time**: At 14:13 on Wednesday, the user requests a restaurant. The restaurants Wednesday opening hours are from 12:00 to 23:00. Since the current time (14:13) is between the opening hours, the restaurant is open when the user makes the request. Thus, the time parameter is CORRECT.
    3. **Cost**: User wants "very budget-friendly" (low); restaurant cost is "high" ⇒ **INCORRECT**
    4. **Rating**: User wants at least 3.6; restaurant rating is 4.6 ⇒ **CORRECT**
    5. **Cuisine**: User wants Italian; restaurant offers Italian ⇒ **CORRECT**

    **Conclusion**: Since **Cost** is **INCORRECT**, the final decision is **false**.

    ---

    **Example 2: Positive Match**

    **User Block:**
    - Location:
        - Latitude: 52.497515324667674
        - Longitude: 13.420960604021236
        - Description: Berlin, Kreuzberg
    - Date: Sat, 07 Sep 2024
    - Time: 18:07
    - User Utterance: "Can you locate a spot where I can get burgers, with medium prices and a rating over 4?"

    **System Block:**
    - Restaurant Name: Burger Brazzo
    - Location:
        - Latitude: 52.489506
        - Longitude: 13.422507
        - Description: Berlin, Kreuzberg
    - Cuisine Type: American
    - Menu: Burgers, Fries, Soft Drinks
    - Cost: medium
    - Rating: 4.2
    - **Opening Hours:**
        - Monday: Closed
        - Tuesday: 08:00-20:00
        - Wednesday: 08:00-20:00
        - Thursday: 08:00-20:00
        - Friday: 08:00-20:00
        - Saturday: 08:00-22:00
        - Sunday: 08:00-22:00
    - Distance in kilometers: 1.4831
    - Duration in minutes: 6

    **Evaluation:**
    1. **Location**: 6 minutes < 15 minutes ⇒ **CORRECT**
    2. **Time**: At 18:07 on Saturday, the user requests a restaurant. The restaurants Saturday opening hours are from 08:00 to 22:00. Since the current time (18:07) is between the opening hours, the restaurant is open when the user makes the request. Thus, the time parameter is CORRECT.
    3. **Cost**: User wants "medium prices"; restaurant cost is "medium" ⇒ **CORRECT**
    4. **Rating**: User wants over 4; restaurant rating is 4.2 ⇒ **CORRECT**
    5. **Cuisine**: User wants burgers; restaurant offers burgers ⇒ **CORRECT**

    **Conclusion**: All parameters are **CORRECT**; the final decision is **true**.

    ---

    **Example 3: Cuisine Error**

    **User Block:**
    - Location:
        - Latitude: 48.151199
        - Longitude: 11.56190
        - Description: Munich, Maxvorstadt
    - Date: Fri, 18 Aug 2023
    - Time: 18:13
    - User Utterance: "Help me find a restaurant that serves German meals, is very easy on the wallet, and has a rating of at least 4.2."

    **System Block:**
    - Restaurant Name: Sophia's Restaurant & Bar
    - Location:
        - Latitude: 48.14251708984375
        - Longitude: 11.564806938171387
        - Description: Munich, Maxvorstadt
    - Cuisine Type: Italian
    - Menu: Pasta, Pizza, Desserts, Drinks
    - Cost: low
    - Rating: 4.3
    - **Opening Hours:**
        - Monday: 18:00-23:00
        - Tuesday: 18:00-23:00
        - Wednesday: 18:00-23:00
        - Thursday: 18:00-23:00
        - Friday: 18:00-23:00
        - Saturday: 18:00-23:00
        - Sunday: 18:00-23:00
    - Distance in kilometers: 2.3
    - Duration in minutes: 9

    **Evaluation:**
    1. **Location**: 9 minutes < 15 minutes ⇒ **CORRECT**
    2. **Time**: At 18:13 on Friday, the user requests a restaurant. The restaurants Friday opening hours are from 18:00 to 23:00. Since the current time (18:13) is between the opening hours, the restaurant is open when the user makes the request. Thus, the time parameter is CORRECT.
    3. **Cost**: User wants "very easy on the wallet" (low); restaurant cost is "low" ⇒ **CORRECT**
    4. **Rating**: User wants at least 4.2; restaurant rating is 4.3 ⇒ **CORRECT**
    5. **Cuisine**: User wants German meals; restaurant offers Italian ⇒ **INCORRECT**

    **Conclusion**: Since **Cuisine** is **INCORRECT**, the final decision is **false**.

    ---

    **Example 4: Time Error**

    **User Block:**
    - Location:
        - Latitude: 48.128861497246476
        - Longitude: 11.571006774902344
        - Description: Munich, Isarvorstadt
    - Date: Sun, 23 Jul 2023
    - Time: 21:12
    - User Utterance: "I need a restaurant with filling, Mediterranean, very affordable food and a rating above 3.8. Can you help?"

    **System Block:**
    - Restaurant Name: Gazzo
    - Location:
        - Latitude: 48.13101972155441
        - Longitude: 11.580836530372856
        - Description: Munich, Glockenbach
    - Cuisine Type: Italian
    - Menu: Pizza, Pasta, Wine, Tiramisu
    - Cost: low
    - Rating: 4.0
    - **Opening Hours:**
        - Monday: 11:00-22:00
        - Tuesday: 11:00-22:00
        - Wednesday: 11:00-22:00
        - Thursday: 11:00-22:00
        - Friday: 11:00-00:00
        - Saturday: 11:00-00:00
        - Sunday: 11:00-21:00
    - Distance in kilometers: 1.1
    - Duration in minutes: 5

    **Evaluation:**
    1. **Location**: 5 minutes < 15 minutes ⇒ **CORRECT**
    2. **Time**: At 21:12 on Sunday, the user requests a restaurant. The restaurants Sunday opening hours are from 11:00 to 21:00. Since the current time (21:12) is NOT between the opening hours, the restaurant is closed when the user makes the request. Thus, the time parameter is INCORRECT.
    3. **Cost**: User wants "very affordable" (low); restaurant cost is "low" ⇒ **CORRECT**
    4. **Rating**: User wants above 3.8; restaurant rating is 4.0 ⇒ **CORRECT**
    5. **Cuisine**: User wants Mediterranean; Italian cuisine is Mediterranean ⇒ **CORRECT**

    **Conclusion**: Since **Time** is **INCORRECT**, the final decision is **false**.

    ---

    **Example 5: Location Error**

    **User Block:**
    - Location:
        - Latitude: 52.50205441987642
        - Longitude: 13.322704758293828
        - Description: Berlin, Charlottenburg
    - Date: Wed, 15 Nov 2023
    - Time: 13:20
    - User Utterance: "Please help me find a restaurant offering vegan and vegetarian dishes, with medium costs, and a decent rating above 4.2."

    **System Block:**
    - Restaurant Name: Copenhagen Deli
    - Location:
        - Latitude: 52.67205441987642
        - Longitude: 13.492704758293828
        - Description: Berlin, Reinickendorf
    - Cuisine Type: Vegan & Vegetarian Salads
    - Menu: Breakfast, Baguettes, Bread, Coffee, Cake, Avocado, Salads
    - Cost: medium
    - Rating: 4.5
    - **Opening Hours:**
        - Monday: Closed
        - Tuesday: 09:30-18:00
        - Wednesday: 09:30-18:00
        - Thursday: 09:30-18:00
        - Friday: 09:30-18:00
        - Saturday: 09:30-18:00
        - Sunday: 09:30-18:00
    - Distance in kilometers: 15.3
    - Duration in minutes: 32

    **Evaluation:**
    1. **Location**: 32 minutes > 15 minutes ⇒ **INCORRECT**
    2. **Time**: At 13:20 on Wednesday, the user requests a restaurant. The restaurants Wednesday opening hours are from 09:30 to 18:00. Since the current time (12:20) is between the opening hours, the restaurant is open when the user makes the request. Thus, the time parameter is CORRECT.
    3. **Cost**: User wants "medium costs"; restaurant cost is "medium" ⇒ **CORRECT**
    4. **Rating**: User wants above 4.2; restaurant rating is 4.5 ⇒ **CORRECT**
    5. **Cuisine**: User wants vegan and vegetarian dishes; restaurant offers vegan and vegetarian ⇒ **CORRECT**

    **Conclusion**: Since **Location** is **INCORRECT**, the final decision is **false**.

    ---

    Now, please evaluate the following case:

    **User Block:**
    - Location:
    - Latitude: {current_gps_user_block.latitude}
    - Longitude: {current_gps_user_block.longitude}
    - Description: {current_gps_user_block.description}
    - Date: {date}
    - Time: {time}
    - User Utterance: "{user_utterance}"

    **System Block:**
    - Restaurant Name: {name}
    - Location: 
        - Latitude: {current_gps_system_block.latitude}, 
        - Longitude: {current_gps_system_block.longitude}, 
        - Description: {current_gps_system_block.description}
    - Cuisine Type: {cuisine_type}
    - Menu: {menu}
    - Cost: {cost}
    - Rating: {rating}
    - Opening Hours: 
        - Monday: {opening_hours.monday}, 
        - Tuesday: {opening_hours.tuesday}, 
        - Wednesday: {opening_hours.wednesday}, 
        - Thursday: {opening_hours.thursday}, 
        - Friday: {opening_hours.friday},
        - Saturday: {opening_hours.saturday}, 
        - Sunday: {opening_hours.sunday},
    - Distance in kilometers: {distance_km},
    - Duration in minutes: {duration_min}

    After looking at all examples, please now make your critical judgement whether the user block aligns with the system block, following the format instructions below. Please think about it carefully.
    Please respond strictly following the format specified below. Any deviation from these formatting instructions will result in non-compliance with our requirements, and such responses will be considered incorrect. 
    {format_instructions}. Make sure the output is always a valid Json format. Make sure the output is always a valid Json format. Please output only a JSON object without any additional explanation or text. Do not include any introductory or concluding remarks!!!
"""
