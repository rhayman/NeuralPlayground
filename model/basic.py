import sys
sys.path.append("../")
import numpy as np
import random
from neuroscience_models_prosecutor.model.core import NeuralResponseModel as NeurResponseModel
import matplotlib.pyplot as plt
import numpy as np

class ExcitInhibitoryplastic(NeurResponseModel):

    def __init__(self, model_name="ExcitInhibitoryplastic",**mod_kwargs):
        super().__init__(model_name,**mod_kwargs)
        self.metadata = {"mod_kwargs": mod_kwargs}
        self.etaexc = mod_kwargs["exc_eta"]  # Learning rate.
        self.etainh = mod_kwargs["inh_eta"]
        self.Ne=mod_kwargs["Ne"]
        self.Ni=mod_kwargs["Ni"]
        self.alpha_exc= mod_kwargs["alpha_exc"]
        self.sigma_exc= mod_kwargs["sigma_exc"]
        self.alpha_inh= mod_kwargs["alpha_inh"]
        self.sigma_inh= mod_kwargs["sigma_inh"]
        self.D = len(self.sigma_exc)  # Stimulus dimensions: punctate and contextual cues.
        self.reset()

    def reset(self):
        self.global_steps = 0
        self.history = []
        self.wi = np.ones((self.D,self.Ne)) #what is the mu and why do we have the 1 and not2
        self.we = np.ones((self.D,self.Ni))
        rout = np.zeros((self.D,1))
 
    def act(self, observation):
        action=np.random.normal(scale=0.1, size=(2,))
        return action
 

    def update(self, x):
        self.global_steps += 1
        self.get_rates_exc= self.alpha_exc*np.exp((x/self.sigma_exc)**2)
        self.get_rates_inh= self.alpha_inh*np.exp((x/self.sigma_inh)**2)
        self.rout = (np.dot(self.we,self.get_rates_exc)- np.dot(self.wi,self.get_rates_inh))
    
        self.we = self.we + self.etaexc * self.get_rates_exc(x)* rout    # Weight update inh
        self.wi = self.wi +  self.etainh * self.get_rates_inh(x) * rout  # Weight update exc
        transition = {"wi": self.wi , "we": self.we, "r_out": rout,}
        self.history.append(transition)
        return rout
    

    
