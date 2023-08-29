from scipy.optimize import least_squares
from DataProcessing import data_smoothing
from scipy.interpolate import CubicSpline
import numpy as np


def residuals(params, multilayer, layer_index, data):
    """
    Calculate the residuals between calculated reflectance and experimental reflectance.

    Parameters:
    - params (list of float): List of parameters [n1, n2, n3, n4, n5, k1, k2, k3, k4, k5, thickness] to be optimized.
    - multilayer (ThinFilmSystem): A ThinFilmSystem to calculate the reflectance.
    - layer_index (int): The index of the layer whose parameters are to be optimized.
    - data (pd.DataFrame): Experimental data where `data['wavelength']` is the wavelength and 
                           `data['reflectance']` is the experimental reflectance.

    Returns:
    - list of float: Residuals = calculated_reflectance - experimental_reflectance.
    """
    # Extract spline control points and thickness from params
    n_control = params[:5]
    k_control = params[5:10]
    thickness = params[10]

    # Put n_control, k_control, and thickness into the multilayer system
    # multilayer.layers[layer_index].n = n_control
    # multilayer.layers[layer_index].k = k_control
    wavelength = multilayer.layers[layer_index].wavelength
    original_n_spline_cubic = CubicSpline(wavelength, n_control)
    multilayer.layers[layer_index].n_spline_cubic = lambda x: np.maximum(
        original_n_spline_cubic(x), 0)
    original_k_spline_cubic = CubicSpline(wavelength, k_control)
    multilayer.layers[layer_index].k_spline_cubic = lambda x: np.maximum(
        original_k_spline_cubic(x), 0)
    multilayer.layers[layer_index].thickness = thickness

    # Calculate the residuals
    wavelength_range = data['wavelength']
    model_reflectance, _, _ = multilayer.calculate_RTA(wavelength_range)
    experimental_reflectance = data['reflectance']
    uncertainty = data['uncertainty']
    residuals = ((1 / uncertainty) *
                 (model_reflectance - experimental_reflectance))

    return residuals


def optimize_nk(multilayer, layer_index, data, smooth=False):
    """
    Optimize the control points of n, k, and the thickness for a specific layer in the multilayer using Levenberg-Marquardt algorithm.

    Parameters:
    - multilayer (ThinFilmSystem): The multilayer system object.
    - layer_index (int): The index of the layer in the multilayer system to be optimized.
    - data (pd.DataFrame): Experimental data where `data['wavelength']` is the wavelength and `data['reflectance']` is the experimental reflectance.

    Returns:
    - optimized_params (list of float): A list containing the optimized values [n1, n2, n3, n4, n5, k1, k2, k3, k4, k5, thickness].
    - R_optimized (list of float): The reflectance calculated using the optimized parameters.
    """
    initial_n = multilayer.layers[layer_index].initial_n
    initial_k = multilayer.layers[layer_index].initial_k
    initial_thickness = multilayer.layers[layer_index].thickness
    initial_params = [*initial_n, *initial_k, initial_thickness]

    print(
        f'Initial n of layer{layer_index} is: {multilayer.layers[layer_index].initial_n}')
    print(
        f'Initial k of layer{layer_index} is: {multilayer.layers[layer_index].initial_k}')

    lower_bounds = [0]*5 + [0]*5 + [0]
    upper_bounds = [3]*5 + [3]*5 + [1000]

    # Optimization using Levenberg-Marquardt algorithm (achieved by the least_squares(...) function)
    if smooth:
        result = least_squares(residuals, initial_params, args=(
            multilayer, layer_index, data_smoothing(data)), bounds=(lower_bounds, upper_bounds))
    else:
        result = least_squares(residuals, initial_params, args=(
            multilayer, layer_index, data), bounds=(lower_bounds, upper_bounds))
    optimized_params = result.x

    # Setting optimized values
    multilayer.layers[layer_index].n = optimized_params[:5]
    multilayer.layers[layer_index].k = optimized_params[5:10]
    multilayer.layers[layer_index].thickness = optimized_params[10]

    print('Optimal n: ', optimized_params[:5])
    print(f'n of layer{layer_index} has been set to: {optimized_params[:5]}')
    print('Optimal k: ', optimized_params[5:10])
    print(
        f'k of layer{layer_index} has been set to: {optimized_params[5:10]}')
    print('Optimal Thickness: ', optimized_params[10])

    wavelength_range = data['wavelength']
    R_optimized, _, _ = multilayer.calculate_RTA(wavelength_range)

    return R_optimized, optimized_params