import pytest
import numpy as np
import das_generator


@pytest.fixture(params=[16000])
def source_signal(request):
    return np.random.randn(request.param)


@pytest.fixture(params=[16000, 44100.5])
def fs(request):
    return request.param


@pytest.fixture(
    params=[
        (1, [2, 1.5, 2]),
        (1, [[2, 1.5, 2]]),
        (2, [[2, 1.5, 2], [1, 1.5, 2]]),
    ]
)
def nMics_r(request):
    return request.param


@pytest.fixture
def nMics(nMics_r):
    return nMics_r[0]


@pytest.fixture
def r(nMics_r):
    return nMics_r[1]


@pytest.fixture(params=[[2, 3.5, 2]])
def s(request):
    return request.param


@pytest.fixture(
    params=[
        [5, 4, 6],
        [5, 4.0, 6.1],
    ]
)
def L(request):
    return request.param


@pytest.fixture(params=[340, 343.1])
def c(request):
    return request.param


@pytest.fixture(params=[2048, 4096])
def n(request):
    return request.param


@pytest.fixture(
    params=[
        (0.4, None),
        (None, [0.1, 0.1, 0.2, 0.2, 0.3, 0.3]),
        (None, [(0.1, 0.1), (0.2, 0.2), (0.3, 0.3)]),
    ]
)
def reverberation_time_beta(request):
    return request.param


@pytest.fixture
def reverberation_time(reverberation_time_beta):
    return reverberation_time_beta[0]


@pytest.fixture
def beta(reverberation_time_beta):
    return reverberation_time_beta[1]


@pytest.fixture(
    params=[
        das_generator.mic_type.omnidirectional,
        das_generator.mic_type.o,
        das_generator.mic_type.hypercardioid,
    ]
)
def mtypes(request):
    return request.param


@pytest.fixture(params=[2, -1])
def order(request):
    return request.param


@pytest.fixture(params=[2, 3])
def dim(request):
    return request.param


@pytest.fixture(params=[0, [np.pi / 2, 0]])
def orientation(request):
    return request.param


@pytest.fixture(params=[True, False])
def hp_filter(request):
    return request.param


def test_parameters(
    source_signal,
    c,
    fs,
    r,
    nMics,
    s,
    L,
    n,
    beta,
    reverberation_time,
    mtypes,
    order,
    dim,
    orientation,
    hp_filter,
):
    receiver_signals = das_generator.generate(
        source_signal,
        c,
        fs,
        r,
        s,
        L,
        beta=beta,
        reverberation_time=reverberation_time,
        nRIR=n,
        mtypes=mtypes,
        order=order,
        dim=dim,
        orientation=orientation,
        hp_filter=hp_filter,
    )

    assert receiver_signals.shape == (source_signal.shape[0], nMics)
    assert not np.all(np.isclose(receiver_signals, 0))


def test_multiple_mics(
    c, fs, s, L, n, reverberation_time, beta, mtypes, order, dim, orientation, hp_filter
):
    length_source_signal = 16000
    source_signal = np.random.randn(length_source_signal)

    out1 = das_generator.generate(
        source_signal,
        c,
        fs,
        [2, 1.5, 2],
        s,
        L,
        beta=beta,
        reverberation_time=reverberation_time,
        nRIR=n,
        mtypes=mtypes,
        order=order,
        dim=dim,
        orientation=orientation,
        hp_filter=hp_filter,
    )

    out2 = das_generator.generate(
        source_signal,
        c,
        fs,
        [[2, 1.5, 2], [1, 1.5, 2]],
        s,
        L,
        beta=beta,
        reverberation_time=reverberation_time,
        nRIR=n,
        mtypes=mtypes,
        order=order,
        dim=dim,
        orientation=orientation,
        hp_filter=hp_filter,
    )

    assert np.allclose(out1[:, 0], out2[:, 0])


@pytest.mark.parametrize(
    "r, s",
    [
        ([2, 3.5, 2], [2, 5.5, 2]),
        ([2, 5.5, 2], [2, 1.5, 2]),
        ([[2, 5.5, 2], [2, 3.5, 2]], [2, 1.5, 2]),
    ],
)
def test_outside_room(r, s):
    source_signal = np.random.randn(16000)
    with pytest.raises(ValueError):
        das_generator.generate(
            source_signal,
            340,
            16000,
            r,
            s,
            L=[5, 4, 6],
            reverberation_time=0.4,
        )


@pytest.mark.parametrize(
    "beta",
    [
        [(0.1, 0.1, 0.2), (0.2, 0.3, 0.3)],
    ],
)
def test_beta_shape(r, s, beta):
    print(beta)
    source_signal = np.random.randn(16000)
    with pytest.raises(AssertionError):
        das_generator.generate(
            source_signal,
            340,
            16000,
            r,
            s,
            L=[5, 4, 6],
            beta=beta,
        )
