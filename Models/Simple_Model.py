#from turtle import forward
import torch
from torch import nn
import numpy as np
import torch.nn.functional as F


class Neural_Net_module(nn.Module):
    def __init__(self,state_size,action_size,layer_sizes=[],activators=nn.ReLU(),dropouts=1):
        super(Neural_Net_module,self).__init__()
        self.state_size=state_size
        self.action_size=action_size
        self.layer_sizes=[state_size]+layer_sizes+[action_size]
        self.activators=(activators if isinstance(activators,list) else [activators for _ in self.layer_sizes[:-1]])
        self.dropouts=(dropouts if isinstance(dropouts,list) else [dropouts for _ in self.layer_sizes[:-1]])
        
        self.Modules=nn.ModuleList(
            [nn.Sequential(nn.Linear(inp,out),act,nn.Dropout(dpo) if dpo!=None else nn.Identity()) for inp,out,act,dpo in zip(self.layer_sizes[:-1],self.layer_sizes[1:],self.activators,self.dropouts)]
        )
    def forward(self,state):
        for layer in self.Modules:
            state=layer(state)
        return state

class Neural_Net_REINFORCE_Actor(nn.Module):
    def __init__(self,state_size,action_size,layer_sizes=[],activators=nn.ReLU(),gamma=0.99):
        super(Neural_Net_REINFORCE_Actor,self).__init__()
        self.gamma=gamma
        self.state_size=state_size
        self.action_size=action_size
        self.layer_sizes=[state_size]+layer_sizes+[action_size]
        self.activators=(activators if isinstance(activators,list) else [activators for _ in self.layer_sizes[:-1]])

        self.Modules=nn.ModuleList(
            [nn.Sequential(nn.Linear(inp,out),act) for inp,out,act in zip(self.layer_sizes[:-1],self.layer_sizes[1:],self.activators)]
        )

        self.losses={"loss":0}
    
    def forward(self,state):
        for layer in self.Modules:
            state=layer(state)
        return state

    def act(self,state):
        return self.forward(state)

    def REINFORCE_loss(self,returns,states,sampled_actions):
        """
        returns: lambda return per steps in batched episodes [ steps_in_episode*episodes*batch_size ]
        states: states per steps in batched episodes [ steps_in_episode*episodes*batch_size ]
        OUTPUTS:
            Losess: Losses per episode
        """
        actions=self.forward(states) # [ steps_in_episode*episodes*batch_size, action_size ]
        logprobs=torch.log(actions)
        selected_logprobs=logprobs[np.arange(actions.shape[0]),sampled_actions]
        losses=-returns*selected_logprobs
        #losses=((returns.detach())*logprobs[np.arange(len(sampled_actions)),sampled_actions])

        return losses #
    


class Neural_Net_Actor_Critic(nn.Module):
    #def __init__(self,state_size,action_size,layer_sizes=[],activators=nn.ReLU(),gamma=0.99):
    def __init__(self,Actor_model,Critic_model,gamma=0.99,norm=(lambda x:x**2)):
        super(Neural_Net_Actor_Critic,self).__init__()
        self.gamma=gamma
        self.losses={"Actor_loss":0,
                     "Critic_loss":0}
        self.Actor=Actor_model
        self.Critic=Critic_model

        self.norm=norm

    def act(self,state):
        return self.Actor.forward(state)
    
    def cri(self,state):
        return self.Critic.forward(state)

    def compute_delta(self,R,gamma,s,s_p,done): #Consider as a constant
        if done:
            return R-self.cri(s)
        else:
            return R+gamma*self.cri(s_p).detach()-self.cri(s)

    def Actor_loss(self,cumulate_gama,delta,states,prob_actions,sampled_actions):

        #prob_actions=self.Actor.forward(states)
        logprobs=torch.log(prob_actions)
        selected_logprobs=logprobs[np.arange(prob_actions.shape[0]),sampled_actions]
        losses=cumulate_gama*delta*selected_logprobs
        return -losses.sum()
    
    def Critic_loss(self,delta,states):

        delta=self.norm(delta)
        #losses=delta*self.Critic.forward(states)
        losses=delta
        return losses.sum()

class Neural_Net_n_step_Actor_Critic(Neural_Net_Actor_Critic):
    def __init__(self,Actor_model,Critic_model,gamma=0.99,norm=(lambda x:x**2)):
        super(Neural_Net_n_step_Actor_Critic,self).__init__(Actor_model,Critic_model,gamma,norm)
    
    def compute_n_delta(self,R,gamma,S,done):
        G=(gamma**np.arange(len(R)))*R+(gamma**len(R))*self.cri(S[-1]).detach()
        delta=G-self.cri(S[0])
        return delta,G
    
    def Actor_loss_nTD(self,cumulate_gama,S,pA,A,R,done):

        S=np.array(S)
        #TODO: modificar para entradas muliples
        logprobs=torch.log(pA) #[n,3]
        selected_logprobs=logprobs[np.arange(pA.shape[0]),A] #[n,1]
        delta=self.compute_delta(R,self.gamma,S[:-1],S[1:],done)
        losses=cumulate_gama*delta*selected_logprobs
        return -losses.sum()
    
    def Actor_loss_G(self,cumulate_gama,S,pA,A,R,done):

        #prob_actions=self.Actor.forward(states)
        logprobs=torch.log(pA)
        selected_logprobs=logprobs[np.arange(pA.shape[0]),A]
        _,G=self.compute_n_delta(self,R,self.gamma,S,done)
        losses=cumulate_gama*G*selected_logprobs
        return -losses.sum()


    #TODO: Decide 
    #OP1: n TD deltas
    #OP2: G_t:t+n
        
        

