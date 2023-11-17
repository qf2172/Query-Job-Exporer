import numpy as np
import scipy
from sqlalchemy import *

RECOMMENDATION_CONFIG = {
   "job_based_num" : 5,
   "preferred_skill_sim_weight" : 1.0,
   "required_skill_sim_weight" : 1.5,
   "job_title_sim_weight" : 0.5,
}


def get_job_similarity(job,title_word_bag, cur_skills):
    """
    Get the similarity between a job and a title_word_bag
    :param job: a job dict "job_title" "required_skills" "preferred_skills"
    :param title_word_bag: a word bag of a title
    :param cur_skills: current skills of a user
    :return: a similarity score
    """
    # job_title_sim = np.mean([1 if word in job["job_title"] else 0 for word in title_word_bag])
    job_title_len = len(job["job_title"].split(' '))
    job_required_skills_len = len(job["required_skills"].split(',')) if job["required_skills"] else 0
    job_preferred_skills_len = len(job["preferred_skills"].split(',')) if job["preferred_skills"] else 0
    job_vector = np.ones(job_title_len+job_required_skills_len+job_preferred_skills_len)
    vector_weights = np.ones(job_vector.shape)
    vector_weights[:job_title_len] = RECOMMENDATION_CONFIG["job_title_sim_weight"]
    vector_weights[job_title_len:job_title_len+job_required_skills_len] = RECOMMENDATION_CONFIG["required_skill_sim_weight"]
    vector_weights[job_title_len+job_required_skills_len:] = RECOMMENDATION_CONFIG["preferred_skill_sim_weight"]
    based_vector = np.zeros(job_vector.shape)
    for i,word in enumerate(job["job_title"].split(' ')):
        if word in title_word_bag:
            based_vector[i] = 1
    if job["required_skills"]:
        for i,skill in enumerate(job["required_skills"].split(',')):
            if skill in cur_skills:
                based_vector[i] = 1
    if job["preferred_skills"]:
        for i,skill in enumerate(job["preferred_skills"].split(',')):
            if skill in cur_skills:
                based_vector[i] = 1
    return scipy.spatial.distance.cosine(job_vector,based_vector, w=vector_weights)
            
def get_location_search_ambiguous_query(partial_location):
    return text("""
        SELECT distinct location
        FROM (
        SELECT location_id, concat(city, ', ', state, ', ', country) as location
        FROM location
        WHERE city LIKE :partial_location
        UNION
        SELECT location_id, concat(state, ', ', country) as location
        FROM location
        WHERE state LIKE :partial_location
        UNION
        SELECT location_id, country as location
        FROM location
        WHERE country LIKE :partial_location) as a
    """), {"partial_location": partial_location+"%"}

def get_location_search_query(partial_location):
    return text("""
        SELECT distinct location_id
        FROM (
        SELECT location_id, concat(city, ', ', state, ', ', country) as location
        FROM location
        WHERE city LIKE :partial_location
        UNION
        SELECT location_id, concat(state, ', ', country) as location
        FROM location
        WHERE state LIKE :partial_location
        UNION
        SELECT location_id, country as location
        FROM location
        WHERE country LIKE :partial_location) as a
    """), {"partial_location": partial_location}

if __name__ == '__main__':
    pass