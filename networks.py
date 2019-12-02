import torch
import torchvision
import torch.nn as nn
import torch.optim as optim
import numpy as np
from torch.utils.data import TensorDataset, DataLoader
import torchvision.transforms as transforms

import layers
from config import device



# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Base Network Class
class Network_Generator():
    def __init__(self, rate_learn, size_batch, size_iter, size_print_every, oj_loss, optimizer, oj_model, collate_fn=None):

        # Params +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        self._rate_learning = rate_learn
        self._size_batch = size_batch
        self._size_iter = size_iter
        self._size_print_every = size_print_every

        # (Function) Objects +++++++++++++++++++++++++++++++++++++++++++++++++++
        self._oj_model = oj_model
        self._oj_optimizer = optimizer(self._oj_model.parameters(), lr = self._rate_learning)
        self._oj_loss = oj_loss
        self._collate_fn = collate_fn


    def test(self, test_dataset, draw=True):
        loader_test = DataLoader(dataset=test_dataset, batch_size=self._size_batch, pin_memory=False, shuffle=True, collate_fn=self._collate_fn)
        checkpoint = torch.load("model/"+ type(self._oj_model).__name__ + "_" + str(device) + ".pt", map_location=lambda storage, loc: storage)
        self._oj_model.load_state_dict(checkpoint)
        del checkpoint  # dereference seems crucial
        torch.cuda.empty_cache()

        with torch.no_grad():
            losses_test_batch = []
            for batch in loader_test:
                self._oj_model.eval()
                # Makes predictions
                volume, coords, labels, actual = batch
                yhat = self._oj_model.inference(volume.to(device), coords.to(device))

                if draw:
                    hits = torch.squeeze(yhat)
                    print("Acitvation", torch.sum(yhat))
                    locs = coords[hits == 1]
                    to_write = locs.cpu().numpy().astype(np.short)
                    # Only each 10th as meshlab crashes otherwise
                    to_write_act = actual[::10,:].cpu().numpy().astype(np.short)
                    with open('outfile_auto.obj','w') as f:
                        for line in to_write:
                            f.write("v " + " " + str(line[0]) + " " + str(line[1]) + " " + str(line[2]) + 
                             " " + "1.0" + " " + "0.0" + " " + "0.0" + "\n")
                        for line in to_write_act:
                            f.write("v " + " " + str(line[0]) + " " + str(line[1]) + " " + str(line[2]) + 
                            " " + "0.0" + " " + "1.0" + " " + "0.0" + "\n")
                    

                loss_test_batch = self._oj_loss(yhat, labels.to(device)).item()
                losses_test_batch.append(loss_test_batch)
        
        #TODO for all batches not only last one
        return loss_test_batch


    # Validate, ignore grads
    def _val(self, loader_val, losses_val):
        with torch.no_grad():
            losses_val_batch = []
            for batch in loader_val:

                self._oj_model.eval()
                # Makes predictions
                volume, coords, labels = batch
                yhat = self._oj_model(volume.to(device), coords.to(device))

                # Computes validation loss
                loss_val_batch = self._oj_loss(yhat, labels.to(device)).item()
                losses_val_batch.append(loss_val_batch)

            loss_val = np.mean(losses_val_batch)
            losses_val.append((loss_val))
            return loss_val


    def train(self, train_dataset, val_dataset, load=False):

        # Function vars ++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        loss_best = float('inf')
        losses_train = []
        losses_val = []
        loader_train = DataLoader(dataset=train_dataset, batch_size=self._size_batch, pin_memory=True, shuffle=True, collate_fn=self._collate_fn)
        loader_val = DataLoader(dataset=val_dataset, batch_size=self._size_batch, pin_memory=True, shuffle=True, collate_fn=self._collate_fn)
        if load:
            self._oj_model.load_state_dict(torch.load( "model/"+ type(self._oj_model).__name__ + "_" + str(device) + ".pt"))
            self._oj_optimizer.load_state_dict(torch.load( "optimizer/"+ type(self._oj_model).__name__ + "_" + str(device) + ".pt"))

        # Auxiliary functions ++++++++++++++++++++++++++++++++++++++++++++++++++
        # Make a training step
        def _step_train(batch):
            volume, coords, labels = batch
            self._oj_model.train()
            yhat = self._oj_model(volume.to(device), coords.to(device))
            loss_train = self._oj_loss(yhat, labels.to(device))
            loss_train.backward()
            self._oj_optimizer.step()
            self._oj_optimizer.zero_grad()
            return loss_train.item()


        # Logic ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        for _ in range(self._size_iter):

            losses_train_batch = []
            for i, batch in enumerate(loader_train):

                # One step of training
                loss_train_batch = _step_train(batch)
                print("Training Loss Batch", i, loss_train_batch,flush=True)

                if i % self._size_print_every == self._size_print_every-1:
                    loss_val = self._val(loader_val, losses_val)
                    print("Validation Loss", loss_val)

                    if loss_val < loss_best:
                        loss_best = loss_val
                        torch.save(self._oj_model.state_dict(), "model/"+ type(self._oj_model).__name__ + "_" + str(device) + ".pt")
                        torch.save(self._oj_optimizer.state_dict(), "optimizer/"+ type(self._oj_model).__name__ + "_" + str(device) + ".pt")

            loss_train = np.mean(losses_train_batch)
            losses_train.append(loss_train)
            print("Training Loss Iteration", loss_train,flush=True)


class Res_Auto_3d_Model_Occu_Parallel(nn.Module):
    def __init__(self):
        super(Res_Auto_3d_Model_Occu_Parallel,self).__init__()

        self.model = nn.DataParallel(Res_Auto_3d_Model_Occu())

    def forward(self, volume, coords):
        return self.model(volume, coords)

    def inference(self, volume, coords):
        return (torch.sign(self.forward(volume, coords) - 0.1) + 1) / 2

class Res_Auto_3d_Model_Occu(nn.Module):
    def __init__(self):
        super(Res_Auto_3d_Model_Occu,self).__init__()

        self.encode = nn.Sequential(layers.Res_Block_Down_3D(1, 16, 3, 1, nn.SELU(), False),
                                    layers.Res_Block_Down_3D(16, 16, 3, 1, nn.SELU(), True),
                                    layers.Res_Block_Down_3D(16, 32, 3, 1, nn.SELU(), True),
                                    layers.Res_Block_Down_3D(32, 16, 3, 1, nn.SELU(), False),
                                    layers.Res_Block_Down_3D(16, 1, 3, 1, nn.SELU(), True))

        self.decode = nn.Sequential(layers.Res_Block_Up_Flat(60 + 3, 128, nn.SELU()),
                                    layers.Res_Block_Up_Flat(128, 256, nn.SELU()),
                                    layers.Res_Block_Up_Flat(256, 128, nn.SELU()),
                                    layers.Res_Block_Up_Flat(128, 1, nn.Sigmoid()))

    def forward(self, volume, coords):
        out = self.encode(volume)
        out = out.view(out.shape[0],-1)
        out = self.decode(torch.cat((torch.repeat_interleave(out, int(coords.shape[0]/volume.shape[0]), dim=0), coords), dim=1))
        print("Activation", torch.sum(out).item()) # See if activated
        return out
    
