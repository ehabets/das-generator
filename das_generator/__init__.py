from __future__ import division
from enum import Enum
import numpy as np
from . import _bindings


class mic_type(Enum):
    """Microphone type."""

    bidirectional = b"b"
    b = b"b"
    cardioid = b"c"
    c = b"c"
    subcardioid = b"s"
    s = b"s"
    hypercardioid = b"h"
    h = b"h"
    omnidirectional = b"o"
    o = b"o"


def generate(
    source_signal,
    c,
    fs,
    rp_path,
    sp_path,
    L,
    beta=None,
    reverberation_time=None,
    nRIR=None,
    mtypes=mic_type.omnidirectional,
    order=-1,
    dim=3,
    orientation=None,
    hp_filter=True,
):
    """Generate room impulse response.

    Parameters
    ----------
    source_signal : float
        Source signal.
    c : float
        Sound velocity in m/s. Usually between 340 and 350.
    fs : float
        Sampling frequency in Hz.
    rp_path : array_like
        2D or 3D array of floats, specifying the :code:`(x, y, z)` coordinates of the receiver(s)
        in m. Must be of shape :code:`(3,)` or :code:`(x, 3)` where :code:`x`
        is the number of receivers.
    sp_path : array_like
        2D array of floats specifying the :code:`(x, y, z)` coordinates of the source in m.
    L : array_like
        1D array of floats specifying the room dimensions :code:`(x, y, z)` in m.
    beta : array_like, optional
        1D array of floats specifying the reflection coefficients

        .. code-block::

            [beta_x1, beta_x2, beta_y1, beta_y2, beta_z1, beta_z2]

        or

        .. code-block::

            [(beta_x1, beta_x2), (beta_y1, beta_y2), (beta_z1, beta_z2)]

        Must be of shape :code:`(6,)` or :code:`(3, 2)`.

        You must define **exactly one** of :attr:`beta` or
        :attr:`reverberation_time`.
    reverberation_time : float, optional
        Reverberation time (T_60) in seconds.

        You must define **exactly one** of :attr:`beta` or
        :attr:`reverberation_time`.
    nRIR : int, optional
        Length of the room impulse responses, default is :code:`T_60 * fs`.
    mtypes : array of mic_type, optional
        Microphone type, one of :class:`mic_type`.
        Defaults to :class:`mic_type.omnidirectional`.
    order : int, optional
        Reflection order, default is :code:`-1`, i.e. maximum order.
    dim : int, optional
        Room dimension (:code:`2` or :code:`3`), default is :code:`3`.
    orientation : array_like, optional
        1D array direction in which the microphones are pointed, specified
        using azimuth and elevation angles (in radians), default is
        :code:`[0, 0]`.
    hp_filter : boolean, optional
        Enable high-pass filter, the high-pass filter is enabled by default.

    Returns
    -------
    receiver_signals : array_like
        The output signal(s), shaped `(len(source_signal), number_of_receivers)`.
    """
    if source_signal.ndim != 1:
        raise ValueError("Error: source_signal must be a 1-dimensional array")

    # More validation before the call
    if c <= 0 or fs <= 0:
        raise ValueError("Speed of sound and sampling frequency must be positive.")

    # Check if L is a list and convert it to a numpy array if necessary
    if isinstance(L, list):
        L = np.array(L)

    rp_path = np.asarray(rp_path, dtype=np.double)
    
    if rp_path.ndim == 1:  # Static position, nMicrophone = 1
        nMicrophones = 1
        assert rp_path.shape == (3,)
        rp_path = rp_path.reshape(1, 3)
        rp_path = np.tile(rp_path[:, :, np.newaxis], (1, 1, source_signal.shape[0]))
    elif rp_path.ndim == 2:  # Static position, nMicrophone > 1
        nMicrophones = rp_path.shape[0]
        assert rp_path.shape[1] == 3
        rp_path = np.tile(rp_path[:, :, np.newaxis], (1, 1, source_signal.shape[0]))
    else:
        nMicrophones = rp_path.shape[0]
        assert rp_path.shape[1:3] == (3, source_signal.shape[0])

    if (rp_path > L[None, :, None]).any() or (rp_path < 0).any():
        raise ValueError("Error: A receiver position in rp_path lies outside the room")

    sp_path = np.asarray(sp_path, dtype=np.double)
    if sp_path.shape == (3,):  # Static position
        assert sp_path.shape[0] == 3
        sp_path = np.tile(sp_path[:, np.newaxis], (1, source_signal.shape[0]))
    else:
        assert sp_path.shape[:2] == (3, source_signal.shape[0])

    if (sp_path > L[:, None]).any() or (sp_path < 0).any():
        raise ValueError("Error: A source position in sp_path lies outside the room")

    L = np.asarray(L, dtype=np.double)
    assert L.shape == (3,)

    if beta is not None:
        beta = np.asarray(beta, dtype=np.double)
        assert beta.shape == (6,) or beta.shape == (3, 2)
        beta = beta.reshape(3, 2)

    if mtypes is None:
        # mtypes is undefined
        mtypes = [mic_type.omnidirectional] * nMicrophones
    elif isinstance(mtypes, mic_type):
        # mtypes is a single instance of mic_type
        mtypes = [mtypes] * nMicrophones
    elif isinstance(mtypes, list) and all(isinstance(m, mic_type) for m in mtypes):
        # mtypes is a list of mic_type instances
        if len(mtypes) != nMicrophones:
            raise ValueError(
                "Error: The length of mtypes should be equal to the number of microphones"
            )
    else:
        raise TypeError(
            "Error: mtypes must be either a mic_type instance or an array of mic_type instances"
        )

    # Make sure orientation is a 2-element array, even if passed a single value
    if orientation is None:
        orientation = np.zeros(2, dtype=np.double)
    else:
        orientation = np.asarray(orientation, dtype=np.double).flatten()
        if len(orientation) == 1:
            orientation = np.append(orientation, 0.0)
        elif len(orientation) == 0:
            orientation = np.zeros(2, dtype=np.double)
    assert orientation.shape == (2,)

    assert order >= -1

    assert dim in (2, 3)

    # Volume of room
    V = np.prod(L)

    # Surface area of walls
    A = L[::-1] * np.roll(L[::-1], 1)

    if beta is not None:
        alpha = np.sum(np.sum(1 - beta**2, axis=1) * np.sum(A))

        reverberation_time = max(
            24 * np.log(10.0) * V / (c * alpha),
            0.128,
        )
    elif reverberation_time is not None:
        if reverberation_time != 0:
            S = 2 * np.sum(A)

            alpha = 24 * np.log(10.0) * V / (c * S * reverberation_time)

            if alpha > 1:
                raise ValueError(
                    "Error: The reflection coefficients cannot be "
                    "calculated using the current room parameters, "
                    "i.e. room size and reverberation time. Please "
                    "specify the reflection coefficients or change the "
                    "room parameters."
                )

            beta = np.full((3, 2), fill_value=np.sqrt(1 - alpha), dtype=np.double)
        else:
            beta = np.zeros((3, 2), dtype=np.double)
    else:
        raise ValueError(
            "Error: Specify either RT60 (ex: reverberation_time=0.4) or "
            "reflection coefficients (beta=[0.3,0.2,0.5,0.1,0.1,0.1])"
        )

    if nRIR is None:
        nRIR = int(reverberation_time * fs)

    if dim == 2:
        beta[-1, :] = 0

    receiver_signals = np.zeros((source_signal.shape[0], nMicrophones), dtype=np.double)

    p_receiver_signals = _bindings.ffi.cast(
        "double*", _bindings.ffi.from_buffer(receiver_signals)
    )
    p_source_signal = _bindings.ffi.cast(
        "double*", _bindings.ffi.from_buffer(source_signal)
    )
    p_rp_path = _bindings.ffi.cast("double*", _bindings.ffi.from_buffer(rp_path))
    p_sp_path = _bindings.ffi.cast("double*", _bindings.ffi.from_buffer(sp_path))
    p_L = _bindings.ffi.cast("double*", _bindings.ffi.from_buffer(L))
    p_beta = _bindings.ffi.cast("double*", _bindings.ffi.from_buffer(beta))
    mtypes_bytes = b"".join(e.value for e in mtypes)
    p_mtypes = _bindings.ffi.cast("char*", _bindings.ffi.from_buffer(mtypes_bytes))
    p_orientation = _bindings.ffi.cast("double*", _bindings.ffi.from_buffer(orientation))

    # Add a try-except block around the FFI call
    try:
        # Optional: Add pre-call validation
        if source_signal.size == 0 or rp_path.size == 0 or sp_path.size == 0:
            raise ValueError("Error: Input arrays cannot be empty")

        # Store return value if the C function returns status codes
        result = _bindings.lib.computeSignal(
            p_receiver_signals,
            p_source_signal,
            int(source_signal.shape[0]),
            float(c),
            float(fs),
            p_rp_path,
            nMicrophones,
            nRIR,
            p_sp_path,
            p_L,
            p_beta,
            p_mtypes,
            order,
            p_orientation,
            1 if hp_filter else 0,
        )

        # Check return value if the function returns status codes
        # Assuming 0 means success and anything else is an error code
        if hasattr(result, '__int__') and result != 0:
            error_msg = f"Unknown error (code: {result})"
            raise RuntimeError(f"C function computeSignal failed: {error_msg}")

    except Exception as e:
        # Catch and re-raise with more context
        raise RuntimeError(f"Error in computeSignal: {str(e)}") from e

    finally:
        pass

    return receiver_signals
