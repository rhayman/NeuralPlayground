import os.path
import numpy as np
import scipy.io as sio
import glob
import matplotlib.pyplot as plt
import pandas as pd
import neuralplayground
import matplotlib as mpl
from IPython.display import display
from neuralplayground.utils import clean_data, get_2D_ratemap
from .experiment_core import Experiment


class Hafting2008Data(Experiment):
    """ Data class for Hafting et al. 2008. https://www.nature.com/articles/nature06957
        The data can be obtained from https://archive.norstore.no/pages/public/datasetDetail.jsf?id=C43035A4-5CC5-44F2-B207-126922523FD9
        This class only consider animal raw animal trajectories and neural recordings
        This class is also used for Sargolini2006Data due to similir data structure
    """

    def __init__(self, data_path: str = None, recording_index: int = None,
                 experiment_name: str = "FullHaftingData", verbose: bool = False):
        """ Hafting2008Data Init

        Parameters
        ----------
        data_path: str
            if None, load the data sample in the package, else load data from given path
        recording_index: int
            if None, load data from default recording index
        experiment_name: str
            string to identify object in case of multiple instances
        verbose:
            if True, it will print original readme and data structure when initializing this object
        """
        self.experiment_name = experiment_name
        self._find_data_path(data_path)
        self._load_data()
        self._create_dataframe()
        self.rat_id, self.sess, self.rec_vars = self.get_recorded_session(recording_index)
        self.set_animal_data()
        if verbose:
            self.show_readme()
            self.show_data()

    def set_animal_data(self, recording_index=0, tolerance=1e-10):
        session_data, rev_vars, rat_info = self.get_recording_data(recording_index)
        tetrode_id = self._find_tetrode(rev_vars)
        time_array, test_spikes, x, y = self.get_tetrode_data(session_data, tetrode_id)

        self.position = np.stack([x, y], axis=1) * 100
        head_direction = np.diff(self.position, axis=0)
        head_direction = head_direction/np.sqrt(np.sum(head_direction**2, axis=1) + tolerance)[..., np.newaxis]
        self.head_direction = head_direction

    def _find_data_path(self, data_path):
        """Set self.data_path to the data directory within the package"""
        if data_path is None:
            self.data_path = os.path.join(neuralplayground.__path__[0], "experiments/hafting_2008/")
        else:
            self.data_path = data_path

    def _load_data(self):
        """ Parse data according to specific data format
        if you are a user check the notebook examples """
        self.best_recording_index = 4
        self.arena_limits = np.array([[-200, 200], [-20, 20]])
        data_path_list = glob.glob(self.data_path + "*.mat")
        mice_ids = np.unique([dp.split("/")[-1][:5] for dp in data_path_list])
        self.data_per_animal = {}
        for m_id in mice_ids:
            m_paths_list = glob.glob(self.data_path + m_id + "*.mat")
            sessions = np.unique([dp.split("/")[-1].split("-")[1][:8] for dp in m_paths_list]).astype(str)
            self.data_per_animal[m_id] = {}
            for sess in sessions:
                s_paths_list = glob.glob(self.data_path + m_id + "-" + sess + "*.mat")
                cell_ids = np.unique([dp.split("/")[-1].split(".")[-2][-4:] for dp in s_paths_list]).astype(str)
                self.data_per_animal[m_id][sess] = {}
                for cell_id in cell_ids:
                    if cell_id == "_POS":
                        session_info = "position"
                    elif "EG" in cell_id:
                        session_info = cell_id[1:]
                    else:
                        session_info = cell_id

                    r_path = glob.glob(self.data_path + m_id + "-" + sess + "*" + cell_id + "*.mat")
                    cleaned_data = clean_data(sio.loadmat(r_path[0]))
                    self.data_per_animal[m_id][sess][session_info] = cleaned_data

    def _create_dataframe(self):
        """ Generate dataframe for easy display and access of data """
        self.list = []
        l = 0
        for rat_id, rat_sess in self.data_per_animal.items():
            for sess, recorded_vars in rat_sess.items():
                self.list.append({"rec_index": l, "rat_id": rat_id, "session": sess,
                                   "recorded_vars": list(recorded_vars.keys())})
                l += 1
        self.recording_list = pd.DataFrame(self.list).set_index("rec_index")

    def show_data(self, full_dataframe: bool = False):
        """ Print of available data

        Parameters
        ----------
        full_dataframe: bool
            if True, it will show all available data, a small sample otherwise

        Returns
        -------
        recording_list: Pandas dataframe
            List of available data, columns with rat_id, recording session and recorded variables
        """
        print("Dataframe with recordings")
        if full_dataframe:
            pd.set_option('display.max_rows', None)
            pd.set_option('display.max_columns', None)
        display(self.recording_list)
        return self.recording_list

    def show_readme(self):
        """ Print original readme of the dataset """
        readme_path = glob.glob(self.data_path + "readme" + "*.txt")[0]
        with open(readme_path, 'r') as fin:
            print(fin.read())

    def get_recorded_session(self, recording_index: int = None):
        """ Get identifiers to sort the experimental data

        Parameters
        ----------
        recording_index: int
            recording identifier, index in pandas dataframe with listed data
        Returns
        -------
        rat_id: str
            rat identifier from experiment
        sess: str
            recording session identifier from experiment
        recorded_vars: list of str
            Variables recorded from a given session
        """
        if recording_index is None:
            recording_index = self.best_recording_index
        list_item = self.recording_list.iloc[recording_index]
        rat_id, sess, recorded_vars = list_item["rat_id"], list_item["session"], list_item["recorded_vars"]
        return rat_id, sess, recorded_vars

    def get_recording_data(self, recording_index: int = None):
        """ Get experimental data for a given recordin index

        Parameters
        ----------
        recording_index: int
            recording identifier, index in pandas dataframe with listed data

        Returns
        -------
        session_data: dict
            Dictionary with recorded raw data from the session of the respective recording index
            Format of this data follows original readme from the authors of the experiments
        rec_vars: list of str
            keys of session_data dict
        identifiers: dict
            Dictionary with rat_id and session_id of the returned session data
        """
        if recording_index is None:
            recording_index = self.best_recording_index
        if type(recording_index) is list or type(recording_index) is tuple:
            data_list = []
            for ind in recording_index:
                rat_id, sess, rec_vars = self.get_recorded_session(ind)
                session_data = self.data_per_animal[rat_id][sess]
                data_list.append([session_data, rec_vars, {"rat_id": rat_id, "session": sess}])
            return data_list
        else:
            rat_id, sess, rec_vars = self.get_recorded_session(recording_index)
            session_data = self.data_per_animal[rat_id][sess]
            identifiers = {"rat_id": rat_id, "sess": sess}
            return session_data, rec_vars, identifiers

    def _find_tetrode(self, rev_vars):
        tetrode_id = next(
            var_name for var_name in rev_vars if (var_name != 'position') and (("t" in var_name) or ("T" in var_name)))
        return tetrode_id

    def get_tetrode_data(self, session_data=None, tetrode_id=None):
        if session_data is None:
            session_data, rev_vars, rat_info = self.get_recording_data(recording_index=0)
            tetrode_id = self._find_tetrode(rev_vars)

        position_data = session_data["position"]
        x1, y1 = position_data["posx"][:, 0], position_data["posy"][:, 0]
        x2, y2 = x1, y1
        # Selecting positional data
        x = np.clip(x2, a_min=self.arena_limits[0, 0], a_max=self.arena_limits[0, 1])
        y = np.clip(y2, a_min=self.arena_limits[1, 0], a_max=self.arena_limits[1, 1])
        time_array = position_data["post"][:]
        tetrode_data = session_data[tetrode_id]
        test_spikes = tetrode_data["ts"][:, ]
        test_spikes = test_spikes[:, 0]
        time_array = time_array[:, 0]

        return time_array, test_spikes, x, y

    def plot_recording_tetr(self, recording_index=None, save_path=None, ax=None, tetrode_id=None):
        if type(recording_index) is list or type(recording_index) is tuple:
            axis_list = []
            for ind in recording_index:
                ind_axis = self.plot_recording_tetr(ind, save_path=save_path, ax=ax, tetrode_id=None)
                axis_list.append(ind_axis)
            return axis_list

        if ax is None:
            f, ax = plt.subplots(1, 1, figsize=(10, 8))

        session_data, rev_vars, rat_info = self.get_recording_data(recording_index)
        if tetrode_id is None:
            tetrode_id = self._find_tetrode(rev_vars)

        arena_width = self.arena_limits[0, 1] - self.arena_limits[0, 0]
        arena_depth = self.arena_limits[1, 1] - self.arena_limits[1, 0]

        time_array, test_spikes, x, y = self.get_tetrode_data(session_data, tetrode_id)

        scale_ratio = 2  # To discretize space
        h, binx, biny = get_2D_ratemap(time_array, test_spikes, x, y, x_size=int(arena_width/scale_ratio),
                                       y_size=int(arena_depth/scale_ratio), filter_result=True)

        self._make_tetrode_plot(h, ax, tetrode_id, save_path)
        return h, binx, biny

    def _make_tetrode_plot(self, h, ax, title, save_path):
        sc = ax.imshow(h, cmap='jet')
        cbar = plt.colorbar(sc, ax=ax, ticks=[np.min(h), np.max(h)], orientation="horizontal")
        cbar.ax.set_xlabel('Firing rate', fontsize=12)
        cbar.ax.set_xticklabels([np.round(np.min(h)), np.round(np.max(h))], fontsize=12)
        ax.set_title(title)
        ax.set_ylabel('width', fontsize=16)
        ax.set_xlabel('depth', fontsize=16)
        ax.set_xticks([])
        ax.set_yticks([])

        if not save_path is None:
            plt.savefig(save_path, bbox_inches="tight")
            plt.close("all")
        else:
            return ax

    def plot_trajectory(self, recording_index=None, save_path=None, ax=None, plot_every=20):
        if type(recording_index) is list or type(recording_index) is tuple:
            axis_list = []
            for ind in recording_index:
                ind_axis = self.plot_trajectory(ind, save_path=save_path, ax=ax, plot_every=plot_every)
                axis_list.append(ind_axis)
            return axis_list

        if ax is None:
            f, ax = plt.subplots(1, 1, figsize=(8, 6))

        session_data, rev_vars, rat_info = self.get_recording_data(recording_index)
        tetrode_id = self._find_tetrode(rev_vars)

        time_array, test_spikes, x, y = self.get_tetrode_data(session_data, tetrode_id)
        self._make_trajectory_plot(x, y, ax, plot_every)

        return x, y, time_array

    def _make_trajectory_plot(self, x, y, ax, plot_every, fontsize=24):

        ax.plot([self.arena_limits[0, 0], self.arena_limits[0, 0]],
                [self.arena_limits[1, 0], self.arena_limits[1, 1]], "C3", lw=3)
        ax.plot([self.arena_limits[0, 1], self.arena_limits[0, 1]],
                [self.arena_limits[1, 0], self.arena_limits[1, 1]], "C3", lw=3)
        ax.plot([self.arena_limits[0, 0], self.arena_limits[0, 1]],
                [self.arena_limits[1, 1], self.arena_limits[1, 1]], "C3", lw=3)
        ax.plot([self.arena_limits[0, 0], self.arena_limits[0, 1]],
                [self.arena_limits[1, 0], self.arena_limits[1, 0]], "C3", lw=3)

        cmap = mpl.cm.get_cmap("plasma")
        norm = plt.Normalize(0, np.size(x))

        aux_x = []
        aux_y = []
        for i in range(len(x)):
            if i % plot_every == 0:
                if i + plot_every >= len(x):
                    break
                x_ = [x[i], x[i + plot_every]]
                y_ = [y[i], y[i + plot_every]]
                aux_x.append(x[i])
                aux_y.append(y[i])
                sc = ax.plot(x_, y_, "-", color=cmap(norm(i)), alpha=0.6) #linewidth=1)
        # ax.set_xticks([])
        # ax.set_yticks([])
        ax.set_ylabel('width', fontsize=fontsize)
        ax.set_xlabel('depth', fontsize=fontsize)
        ax.set_title("position", fontsize=fontsize)
        ax.grid()

        cmap = mpl.cm.get_cmap("plasma")
        norm = plt.Normalize(0, np.size(x))
        sc = ax.scatter(aux_x, aux_y, c=np.arange(len(aux_x)), vmin=0, vmax=len(x), cmap="plasma", alpha=0.6, s=0.1)

        cbar = plt.colorbar(sc, ax=ax, ticks=[0, len(x)])
        cbar.ax.tick_params(labelsize=fontsize)
        cbar.ax.set_ylabel('N steps', rotation=270, fontsize=fontsize)
        cbar.ax.set_yticklabels([0, len(x)], fontsize=fontsize)
        ax.set_xlim([np.amin([x.min(), y.min()])-1.0, np.amax([x.max(), y.max()])+1.0])
        ax.set_ylim([np.amin([x.min(), y.min()])-1.0, np.amax([x.max(), y.max()])+1.0])
