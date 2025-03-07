from policy import POLICIES

entity_extractor_prompt = """
Please read the given comment and determine what distinct entities are mentioned in the text.
These entities could be logical, institutional, physical, or any other kind of entity.
The exception should be dates, times, or other ubiquitous entities that are not characteristic of the text.
Also excluded specific identifiers like account numbers, PII, or names, unless referring to a public figure or some such publicly known entity.
The entities can be named by single words, phrases, or a sentence.  Each should also have a description that briefly explains what the entity is.
Additionally, provide a quote from the comment from which the entity was extracted.  This can just be a snippet, it doesn't need to be a complete sentence.
If no qualifying entities are present, return an empty list: {"entities": []}
The output should be an array of entities, each with a name and description, with the following format:

{
    "entities": [
        {
            "name": Name of the entity (lowercase),
            "description": Description of the entity,
            "quote": Quote from the comment
        },
        {
            "name": Name of the entity (lowercase),
            "description": Description of the entity,
            "quote": Quote from the comment
        },
        ...
    ]
}
"""

state_observation_prompt = f"""
Please read the conversation and determine the current state of the interaction as of the most recent comment in 1-2 sentences.
This should include the problem being solved, the current topic of discussion, and the sentiment of the customer.
Do not mention "this" conversation, or "this" customer or representative, but rather describe the situation in abstract terms (i.e., "the" customer, "the" account, etc.).
Please do not mention next steps - this is a snapshot of the current state only.

When evaluating the state, please consider the following policies and distinugish states based on whether they are satisfied, in additional to general characteristics as described above:
{"\n".join(POLICIES)}

The output should be a JSON object with the following format:

{{
    "state": "Description of the current state of the conversation"
}}
"""

action_selection_prompt = """
Please read the conversation and determine what action was taken based on the most recent comment.
The action is inferred from the most recent comment and the context of the conversation.
The action should be described in 1 sentence, 2 max if necessary.
Do not say who took the action, but rather say abstractly what the action was.  Respond as if you are figuring out what the employee was told to do before the most recent comment.
For instance, instead of saying, "The employee asked the customer for their account number," you would say, "Ask for the customer's account number."
Also do not ascribe any reasoning or motivation to the action, just describe the action itself.
The output should be a JSON object with the following format:

{
    "action": "Description of the action taken"
}
"""

decision_inference_prompt = """
Please read the conversation and infer what decision was made based on the most recent comment.
The most recent comment represents the decision that was made, so you should infer what the decision was based on the context of the conversation and the transition from the previous comments to the most recent one.
Look at the conversation leading up to the most recent comment, then look at the most recent comment itself, and infer what the critical factors were in the thought process.
The decision should be described in a few sentences, no more than 1 paragraph.
Don't say who made the decision, but describe the likely chain of thought involved in making the decision.
When you have determined the decision made, provide a very brief (less than or equal to 1 phrase) name for it.
The output should be a JSON object with the following format:

{
    "decision": "Description of the decision made"
}
"""

resolution_inference_prompt = """
In 1-2 sentences, please describe the resolution of the call with the transcript provided.
The resolution should describe the final state of the call, the outcome, the customer sentiment, and the favorability of the outcome to the service provider.
The favorability is determined by whether the customer retains their services or increases their spend, as well as how much time or expense the service provider incurred in resolving it.
Provide the output in the following format:

{
    "resolution": "Description of the resolution"
}
"""

def group_description_prompt(mode):
    
    return f"""
You are an AI designed to distill text passages based on their thematic similarities. Your task is to process a set of text strings and generate the following outputs:

Description {"(1 sentence)" if mode == "Action" else "(2 sentences max)"}: {"The core action that distills the essential meaning of the list of actions." if mode == "Action" else "Clearly describe the shared themes without referring to the existence of a collection or the act of summarization. Focus on the core issues, sentiments, and actions."}
Name (less than 1 sentence): Provide a concise, descriptive label that captures the common theme.
Avoid phrases like 'the content,' 'the text,' or 'the collection'—instead, directly present the themes and insights.

For example, given the following content, here is an example of a description and name:

{"""
Content:
"Request the customer's account number to check the status."
"Request the customer's account number to check the service status."
"Request the customer's account number to check their connection status."
"Request the customer's account number to check their service."
"Request the customer's account number to check their current plan."
"Request the customer's account number to check their current plan."
"Request the customer's account number to review the bill"
"Request the customer's account number to review the charges."
"Request the customer's account number to review the bills."

Answer:
{
    "name": "Request Account Number",
    "description": "Ask the customer for their account number."
}
""" if mode == "Action" else """
Content:
"The customer is experiencing internet connectivity issues that occur specifically during rain, which has been linked to potential corrosion caused by bird droppings on the external wiring. The sentiment is positive as the customer is receptive to the employee's suggestion to clean the affected areas."
"The customer is experiencing ongoing intermittent internet outages that are impacting their business, expressing frustration over the situation. The employee is actively troubleshooting by checking for external interference and has already attempted several solutions, including restarting the router and updating firmware. The conversation reflects a sense of urgency and concern from the customer."
"The customer is experiencing ongoing issues with slow internet speed despite having already restarted their router multiple times. The sentiment is one of frustration as the customer seeks further assistance after initial troubleshooting steps were ineffective."
"The customer is experiencing unreliable internet connectivity, which has been an issue for the past week. The employee is currently gathering information to troubleshoot the problem, and the customer has provided details about the location of their modem and router."
"The customer is experiencing intermittent internet connectivity issues that correlate with rainy weather. The employee is actively troubleshooting the problem by asking for the customer's account details and conducting basic checks regarding the router's location. The sentiment is cooperative, with both parties engaged in problem-solving."
"The customer is experiencing ongoing issues with their internet connection, which has been unreliable for a week despite multiple attempts to reboot the modem and router. The sentiment is one of frustration as the customer seeks a resolution to the recurring problem."
"The customer is experiencing an internet connectivity issue that occurs specifically during rain, while other electronic devices function normally. The employee is actively troubleshooting the problem by asking questions about the router's location and other devices."

Answer:
{
    "name": "Intermittent and Weather-Related Internet Connectivity Issues",
    "description": "Customers are experiencing internet connectivity issues, often intermittent or weather-related, leading to frustration and a need for troubleshooting. Employees are actively working to diagnose the problems by gathering information, checking external factors, and suggesting solutions, with varying levels of cooperation from customers."
}
"""}

Note also that the lines of content are ranked with importance scores, so please weight these appropriately in your analysis.
The output should be a JSON object with the following format:

{{
    "name": "Generated name",
    "description": {"The distilled action statement" if mode == "Action" else "Description of the main ideas or themes"}
}}
"""