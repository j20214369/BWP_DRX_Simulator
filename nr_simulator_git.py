import numpy as np
from matplotlib import pyplot as plt

def default_params():
  packet_params = {
      'packet_size':(5,15), #(5,8) means size = 5,6,7,8
      'Mean_arrival_rate':0.05, #Poisson
  }
  DRX_params = {
      'DRX_cycle_time' : 3200, 
      'Buffer_size' : 100, 
      'Inactive_timer' : 100, 
  }
  BWP_params = {
      'Switch_Threshold' : 30, 
      'High_BWP_consumption' : 15 ,
      'Low_BWP_consumption' : 5 ,
  }
  return [packet_params, DRX_params, BWP_params]

def init_state_stat():
  stat = {
      'Active_H' : 0,
      'Inactive_H' : 0,
      'Active_L' : 0,
      'Inactive_L' : 0,
      'Sleep' : 0,
    }
  return stat

def init_packet_stat():
  stat = {
      'Packet_recieve' : 0,
      'Packet_loss' : 0,
      'Packet_delay' : 0,
    }
  return stat

def digits(num, d):
  return int (num * pow(10,d)) / pow(10,d)

class UE:
  def __init__(self, params):
    [self.packet_params,self.DRX_params,self.BWP_params] = params
    self.label = self.DRX_params['label']
    self.sim_time = 20000 
    self.stat = init_state_stat()
    self.pkt_stat = init_packet_stat()
    self.simulation_clock = 0
    self.inactive_timer = 0
    self.DRX_buffer = 0
    self.DRX_counter = 0 #add
    self.state = 'Active_L'
    self.power_consumption = {
      'Active_H' : self.BWP_params['H'],
      'Inactive_H' : self.BWP_params['H'] / 3,
      'Active_L' : self.BWP_params['L'],
      'Inactive_L' : self.BWP_params['L'] / 3,
      'Sleep' : 1,
    }
    self.delay = 0
    

  def simulation(self, next = 0):
    if(self.DRX_counter == 0): 
      self.inactive_timer = 0
      self.DRX_counter = self.DRX_params['short_DRX']
      if (self.DRX_buffer > self.BWP_params['Switch_Threshold'] or self.BWP_params['Switch_Threshold'] == 0):
        self.state = 'Active_H'
      else:
        self.state = 'Active_L'

    # Update every time slot
    self.stat[self.state] += 1
    # First, get packet
    packet_num = np.random.poisson(self.packet_params['Mean_arrival_rate'])
    packet_size = np.random.randint(self.packet_params['packet_size'][0], self.packet_params['packet_size'][1] + 1, packet_num)
    self.pkt_stat['Packet_delay'] += self.DRX_buffer
    self.pkt_stat['Packet_recieve'] += packet_size.sum()
    self.DRX_buffer += packet_size.sum()
    if(self.DRX_buffer > self.DRX_params['Buffer_size']):
      self.pkt_stat['Packet_loss'] += self.DRX_buffer - self.DRX_params['Buffer_size']
      self.DRX_buffer = self.DRX_params['Buffer_size']
    
    # DRX process
    if (self.state == 'Active_H'):
      self.DRX_buffer -= self.BWP_params['High_BWP_consumption']
      if self.DRX_buffer <= 0:
        self.DRX_buffer = 0
        self.state = 'Inactive_H'
        if self.DRX_params['BWP_Inac']==0:
          self.state = 'Inactive_L'

    elif (self.state == 'Inactive_H'):
      if (self.DRX_buffer > 0):
        self.state = 'Active_H'
        self.inactive_timer = 0
      else:
        self.inactive_timer += 1
        if (self.inactive_timer >= self.DRX_params['BWP_Inac']):
          #self.inactive_timer = 0
          self.state = 'Inactive_L'
        if (self.inactive_timer >= self.DRX_params['Inactive_timer']):
          self.inactive_timer = 0
          self.state = 'Sleep'
    elif (self.state == 'Active_L'):
      self.prev_state = self.state
      if next==1:
        if self.DRX_buffer > self.BWP_params['Switch_Threshold']:
          self.state = 'Active_H'
      self.DRX_buffer -= self.BWP_params['Low_BWP_consumption']
      if self.DRX_buffer <= 0:
        self.DRX_buffer = 0
        self.state = 'Inactive_L'
 
    elif (self.state == 'Inactive_L'):
      if (self.DRX_buffer > 0):
        self.state = 'Active_L'
        self.inactive_timer = 0
      else:
        self.inactive_timer += 1
        if (self.inactive_timer >= self.DRX_params['Inactive_timer']):
          self.inactive_timer = 0
          self.state = 'Sleep'    
    else:
      1# Sleep, do nothing
    
    self.simulation_clock += 1
    self.DRX_counter -= 1

  def DRX_sim(self,duration, label = 0):
    for i in range(duration):
      self.simulation(label)
    return self.print_stat()

  def print_stat(self):
    stat = init_state_stat()
    power = 0
    for i in self.stat:
      stat[i] = self.stat[i]/self.simulation_clock
      power += stat[i] * self.power_consumption[i]
      stat[i] = digits(stat[i], 4)
    
    pkt = {
        'Average Packet Delay': digits(self.pkt_stat['Packet_delay'] / (self.pkt_stat['Packet_recieve'] - self.pkt_stat['Packet_loss']), 2),
        'Average Packet Loss': digits(self.pkt_stat['Packet_loss'] / self.pkt_stat['Packet_recieve'], 4),
        'Throughput': self.pkt_stat['Packet_recieve'] - self.pkt_stat['Packet_loss'],
        'Energy per RB': 0,
    }
    pkt['Energy per RB'] = power/pkt['Throughput']
    power = digits(power, 3)
    return stat,pkt,power

def wrapper(s):
  state_stat, pkt_stat, power_stat = s.DRX_sim(s.sim_time, s.label)
  out = [s.packet_params, s.DRX_params, s.BWP_params, state_stat, pkt_stat, {'Average power':power_stat}, s.pkt_stat, s.stat]
  return out

def multi(UE_list):
  import multiprocessing
  p = multiprocessing.Pool()
  return p.map(wrapper, UE_list)

def save_stat(stat, savepath):
  path = savepath + 'v'
  from pathlib import Path

  for i in range(10000):
    filename = path+str(i)+'.txt'
    my_file = Path(filename)
    if my_file.is_file():
      1
      #print('Error, file exist')
    else:
      import pickle
      with open(filename, 'wb') as f:
          pickle.dump(stat, f)
      print('Save at', filename)
      return savepath + 'v' + str(i)

import numpy as np
UE_list = []

# Main
fig_legend = [1, 'short_DRX', 'Mean_arrival_rate'] #[legend position,legend label,xlabel]
sv_path = 'test'
savepath = sv_path + '_original_'

slot_time = 2 #slot/ms

x = [20,200]

for cyc in [80,320,1280]:
  for scale in x: 
    packet_params = {
        'packet_size':(100,200), #(5,8) means size = 5,6,7,8 
        'Mean_arrival_rate': 0.0001 * scale /slot_time, #pkt/ms # rb/sec * sec/ms * ms/slot *pkt/rb,  
    }
    b = 1000
    IN = 10
    BIN = 10
    DRX_params = {
        'short_DRX' : cyc * slot_time, #ms * slot/ms 
        'Buffer_size' :b, 
        'Inactive_timer' : IN * slot_time, #ms * slot/ms
        'BWP_Inac': BIN * slot_time,
        'label': 0,
    }

    H = 19
    L=1
    BWP_params = {
        'Switch_Threshold' :  500,
        'High_BWP_consumption' : H, #/1000 /slot_time, # rb/sec * sec/ms * ms/slot
        'Low_BWP_consumption' : L, #/1000 /slot_time, # rb/sec * sec/ms * ms/slot
        'H' :300/H*H,
        'L' :300/H*L,
    }
    param = [packet_params, DRX_params, BWP_params]

    s = UE(param)
    UE_list.append(s)

out = multi(UE_list)
out2 = [x, fig_legend, out]
savepath = save_stat(out2, savepath)

print(out)